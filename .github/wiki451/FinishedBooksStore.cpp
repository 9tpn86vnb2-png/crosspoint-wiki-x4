#include "FinishedBooksStore.h"

#include <HalStorage.h>
#include <Logging.h>

#include <algorithm>
#include <array>
#include <cstdint>
#include <limits>
#include <string>
#include <vector>

#include "RecentBooksStore.h"

namespace {
constexpr std::array<uint8_t, 4> MAGIC{{'X', 'F', 'B', '1'}};
constexpr const char* TEMP_PATH = "/.crosspoint/finished-books.tmp";
constexpr uint32_t RECORD_HEADER_BYTES = 8;
constexpr uint32_t MAX_RECORD_BYTES = 32768;

struct RecordLengths {
  uint16_t path = 0;
  uint16_t title = 0;
  uint16_t author = 0;
  uint16_t cover = 0;

  uint32_t payloadBytes() const {
    return static_cast<uint32_t>(path) + title + author + cover;
  }
};

bool readExact(HalFile& file, void* data, size_t size) {
  auto* p = static_cast<uint8_t*>(data);
  while (size) {
    const int got = file.read(p, size);
    if (got <= 0) return false;
    p += got;
    size -= static_cast<size_t>(got);
  }
  return true;
}

bool writeExact(HalFile& file, const void* data, size_t size) {
  const auto* p = static_cast<const uint8_t*>(data);
  while (size) {
    const size_t wrote = file.write(p, size);
    if (!wrote) return false;
    p += wrote;
    size -= wrote;
  }
  return true;
}

bool readU16(HalFile& file, uint16_t& value) {
  uint8_t bytes[2];
  if (!readExact(file, bytes, sizeof(bytes))) return false;
  value = static_cast<uint16_t>(bytes[0] | (static_cast<uint16_t>(bytes[1]) << 8));
  return true;
}

bool writeU16(HalFile& file, uint16_t value) {
  const uint8_t bytes[2] = {static_cast<uint8_t>(value & 0xff), static_cast<uint8_t>(value >> 8)};
  return writeExact(file, bytes, sizeof(bytes));
}

bool readLengths(HalFile& file, RecordLengths& lengths) {
  if (!readU16(file, lengths.path) || !readU16(file, lengths.title) ||
      !readU16(file, lengths.author) || !readU16(file, lengths.cover)) {
    return false;
  }
  return lengths.path > 0 && lengths.payloadBytes() <= MAX_RECORD_BYTES;
}

bool writeLengths(HalFile& file, const RecordLengths& lengths) {
  return writeU16(file, lengths.path) && writeU16(file, lengths.title) &&
         writeU16(file, lengths.author) && writeU16(file, lengths.cover);
}

bool readMagic(HalFile& file) {
  std::array<uint8_t, 4> magic{};
  return readExact(file, magic.data(), magic.size()) && magic == MAGIC;
}

bool writeMagic(HalFile& file) { return writeExact(file, MAGIC.data(), MAGIC.size()); }

bool ensureCatalogFile() {
  Storage.mkdir("/.crosspoint");
  if (Storage.exists(FinishedBooksStore::FILE_PATH)) {
    HalFile file = Storage.open(FinishedBooksStore::FILE_PATH, O_RDONLY);
    const bool ok = file && readMagic(file);
    file.close();
    if (!ok) LOG_ERR("FIN", "Invalid finished-books catalog header");
    return ok;
  }

  HalFile file = Storage.open(FinishedBooksStore::FILE_PATH, O_WRONLY | O_CREAT);
  if (!file) return false;
  const bool ok = writeMagic(file);
  file.flush();
  file.close();
  return ok;
}

bool stringFitsRecord(const std::string& value) {
  return value.size() <= std::numeric_limits<uint16_t>::max();
}

bool makeLengths(const RecentBook& book, RecordLengths& lengths) {
  if (book.path.empty() || !stringFitsRecord(book.path) || !stringFitsRecord(book.title) ||
      !stringFitsRecord(book.author) || !stringFitsRecord(book.coverBmpPath)) {
    return false;
  }
  lengths.path = static_cast<uint16_t>(book.path.size());
  lengths.title = static_cast<uint16_t>(book.title.size());
  lengths.author = static_cast<uint16_t>(book.author.size());
  lengths.cover = static_cast<uint16_t>(book.coverBmpPath.size());
  return lengths.payloadBytes() <= MAX_RECORD_BYTES;
}

bool writeRecord(HalFile& file, const RecentBook& book) {
  RecordLengths lengths;
  if (!makeLengths(book, lengths) || !writeLengths(file, lengths)) return false;
  return writeExact(file, book.path.data(), book.path.size()) &&
         writeExact(file, book.title.data(), book.title.size()) &&
         writeExact(file, book.author.data(), book.author.size()) &&
         writeExact(file, book.coverBmpPath.data(), book.coverBmpPath.size());
}

bool readString(HalFile& file, const uint16_t length, std::string& out) {
  out.resize(length);
  return length == 0 || readExact(file, out.data(), length);
}

bool readRecordPayload(HalFile& file, const RecordLengths& lengths, RecentBook& book) {
  return readString(file, lengths.path, book.path) &&
         readString(file, lengths.title, book.title) &&
         readString(file, lengths.author, book.author) &&
         readString(file, lengths.cover, book.coverBmpPath);
}

bool skipPayload(HalFile& file, const RecordLengths& lengths) {
  return file.seekCur(lengths.payloadBytes());
}

bool pathMatchesAndSkip(HalFile& file, const RecordLengths& lengths, const std::string& path) {
  bool matches = false;
  if (lengths.path == path.size()) {
    std::string stored;
    if (!readString(file, lengths.path, stored)) return false;
    matches = stored == path;
  } else if (!file.seekCur(lengths.path)) {
    return false;
  }
  const uint32_t remaining = static_cast<uint32_t>(lengths.title) + lengths.author + lengths.cover;
  if (remaining && !file.seekCur(remaining)) return false;
  return matches;
}

bool rewriteCatalog(const std::string& matchPath, const std::string* replacementPath,
                    const std::string* oldCachePath, const std::string* newCachePath,
                    bool removeMatch, bool& changed) {
  changed = false;
  if (!Storage.exists(FinishedBooksStore::FILE_PATH)) return false;

  HalFile in = Storage.open(FinishedBooksStore::FILE_PATH, O_RDONLY);
  if (!in || !readMagic(in)) {
    if (in) in.close();
    return false;
  }

  Storage.remove(TEMP_PATH);
  HalFile out = Storage.open(TEMP_PATH, O_WRONLY | O_CREAT);
  if (!out || !writeMagic(out)) {
    if (out) out.close();
    in.close();
    Storage.remove(TEMP_PATH);
    return false;
  }

  const uint64_t fileSize = in.fileSize64();
  bool ok = true;
  while (static_cast<uint64_t>(in.position()) + RECORD_HEADER_BYTES <= fileSize) {
    RecordLengths lengths;
    if (!readLengths(in, lengths) ||
        static_cast<uint64_t>(in.position()) + lengths.payloadBytes() > fileSize) {
      ok = false;
      break;
    }

    RecentBook book;
    if (!readRecordPayload(in, lengths, book)) {
      ok = false;
      break;
    }

    if (book.path == matchPath) {
      changed = true;
      if (removeMatch) continue;
      if (replacementPath) {
        book.path = *replacementPath;
        if (oldCachePath && newCachePath && !oldCachePath->empty() && !book.coverBmpPath.empty() &&
            book.coverBmpPath.rfind(*oldCachePath, 0) == 0) {
          book.coverBmpPath = *newCachePath + book.coverBmpPath.substr(oldCachePath->size());
        }
      }
    }

    if (!writeRecord(out, book)) {
      ok = false;
      break;
    }
  }

  out.flush();
  out.close();
  in.close();

  if (!ok) {
    Storage.remove(TEMP_PATH);
    return false;
  }
  if (!changed) {
    Storage.remove(TEMP_PATH);
    return false;
  }

  if (!Storage.remove(FinishedBooksStore::FILE_PATH) ||
      !Storage.rename(TEMP_PATH, FinishedBooksStore::FILE_PATH)) {
    LOG_ERR("FIN", "Failed to replace finished-books catalog");
    Storage.remove(TEMP_PATH);
    return false;
  }
  return true;
}

bool seekChronologicalRecord(HalFile& file, const FinishedBooksCatalog& catalog, const uint32_t index) {
  if (index >= catalog.count || catalog.checkpoints.empty()) return false;
  const uint32_t checkpointIndex = index / FinishedBooksCatalog::CHECKPOINT_STRIDE;
  if (checkpointIndex >= catalog.checkpoints.size() || !file.seek(catalog.checkpoints[checkpointIndex])) return false;

  const uint32_t checkpointRecord = checkpointIndex * FinishedBooksCatalog::CHECKPOINT_STRIDE;
  for (uint32_t i = checkpointRecord; i < index; ++i) {
    RecordLengths lengths;
    if (!readLengths(file, lengths) || !skipPayload(file, lengths)) return false;
  }
  return true;
}
}  // namespace

bool FinishedBooksStore::add(const RecentBook& book) {
  if (!ensureCatalogFile()) return false;
  if (contains(book.path)) return true;

  HalFile file = Storage.open(FILE_PATH, O_WRONLY);
  if (!file || !file.seek(file.size())) {
    if (file) file.close();
    return false;
  }
  const bool ok = writeRecord(file, book);
  file.flush();
  file.close();
  if (!ok) LOG_ERR("FIN", "Failed to append finished book");
  return ok;
}

bool FinishedBooksStore::contains(const std::string& path) {
  if (!Storage.exists(FILE_PATH)) return false;

  HalFile file = Storage.open(FILE_PATH, O_RDONLY);
  if (!file || !readMagic(file)) {
    if (file) file.close();
    return false;
  }

  const uint64_t fileSize = file.fileSize64();
  while (static_cast<uint64_t>(file.position()) + RECORD_HEADER_BYTES <= fileSize) {
    RecordLengths lengths;
    if (!readLengths(file, lengths) ||
        static_cast<uint64_t>(file.position()) + lengths.payloadBytes() > fileSize) {
      break;
    }
    const bool matches = pathMatchesAndSkip(file, lengths, path);
    if (matches) {
      file.close();
      return true;
    }
  }
  file.close();
  return false;
}

bool FinishedBooksStore::removeByPath(const std::string& path) {
  bool changed = false;
  const bool ok = rewriteCatalog(path, nullptr, nullptr, nullptr, true, changed);
  if (changed && !ok) LOG_ERR("FIN", "Failed to remove finished book");
  return changed && ok;
}

bool FinishedBooksStore::updatePath(const std::string& oldPath, const std::string& newPath,
                                    const std::string& oldCachePath, const std::string& newCachePath) {
  bool changed = false;
  const bool ok = rewriteCatalog(oldPath, &newPath, &oldCachePath, &newCachePath, false, changed);
  if (changed && !ok) LOG_ERR("FIN", "Failed to update finished-book path");
  return !changed || ok;
}

bool FinishedBooksStore::buildCatalog(FinishedBooksCatalog& catalog) {
  catalog.clear();
  if (!Storage.exists(FILE_PATH)) return true;

  HalFile file = Storage.open(FILE_PATH, O_RDONLY);
  if (!file || !readMagic(file)) {
    if (file) file.close();
    return false;
  }

  const uint64_t fileSize = file.fileSize64();
  while (static_cast<uint64_t>(file.position()) + RECORD_HEADER_BYTES <= fileSize) {
    const uint32_t recordOffset = static_cast<uint32_t>(file.position());
    if ((catalog.count % FinishedBooksCatalog::CHECKPOINT_STRIDE) == 0) {
      catalog.checkpoints.push_back(recordOffset);
    }

    RecordLengths lengths;
    if (!readLengths(file, lengths) ||
        static_cast<uint64_t>(file.position()) + lengths.payloadBytes() > fileSize ||
        !skipPayload(file, lengths)) {
      if ((catalog.count % FinishedBooksCatalog::CHECKPOINT_STRIDE) == 0 && !catalog.checkpoints.empty()) {
        catalog.checkpoints.pop_back();
      }
      break;
    }
    catalog.count++;
  }
  file.close();
  return true;
}

bool FinishedBooksStore::loadNewestWindow(const FinishedBooksCatalog& catalog, const uint32_t firstNewest,
                                          const uint16_t count, std::vector<RecentBook>& out) {
  out.clear();
  if (count == 0 || firstNewest >= catalog.count) return true;
  const uint32_t available = catalog.count - firstNewest;
  const uint32_t wanted = std::min<uint32_t>(count, available);
  const uint32_t chronoFirst = catalog.count - firstNewest - wanted;

  HalFile file = Storage.open(FILE_PATH, O_RDONLY);
  if (!file || !readMagic(file) || !seekChronologicalRecord(file, catalog, chronoFirst)) {
    if (file) file.close();
    return false;
  }

  out.reserve(wanted);
  for (uint32_t i = 0; i < wanted; ++i) {
    RecordLengths lengths;
    RecentBook book;
    if (!readLengths(file, lengths) || !readRecordPayload(file, lengths, book)) {
      file.close();
      out.clear();
      return false;
    }
    out.push_back(std::move(book));
  }
  file.close();

  std::reverse(out.begin(), out.end());
  return true;
}
