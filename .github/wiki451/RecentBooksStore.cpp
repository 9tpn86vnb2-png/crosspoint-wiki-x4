#include "RecentBooksStore.h"

#include <Epub.h>
#include <FsHelpers.h>
#include <HalStorage.h>
#include <Logging.h>
#include <Xtc.h>

#include <algorithm>
#include <iterator>

#include "FinishedBooksStore.h"

void RecentBooksStore::toJson(JsonDocument& doc) const {
  JsonArray arr = doc["books"].to<JsonArray>();
  for (const auto& book : recentBooks) {
    JsonObject obj = arr.add<JsonObject>();
    obj["path"] = book.path;
    obj["title"] = book.title;
    obj["author"] = book.author;
    obj["coverBmpPath"] = book.coverBmpPath;
  }
}

bool RecentBooksStore::fromJson(JsonVariantConst doc) {
  recentBooks.clear();
  JsonArrayConst arr = doc["books"].as<JsonArrayConst>();
  recentBooks.reserve(std::min(arr.size(), static_cast<size_t>(MAX_RECENT_BOOKS)));
  for (JsonObjectConst obj : arr) {
    if (getCount() >= MAX_RECENT_BOOKS) break;
    RecentBook book;
    book.path = obj["path"] | "";
    book.title = obj["title"] | "";
    book.author = obj["author"] | "";
    book.coverBmpPath = obj["coverBmpPath"] | "";
    recentBooks.push_back(std::move(book));
  }

  JsonArrayConst legacyFinished = doc["finished"].as<JsonArrayConst>();
  bool migrated = false;
  for (JsonObjectConst obj : legacyFinished) {
    RecentBook book;
    book.path = obj["path"] | "";
    book.title = obj["title"] | "";
    book.author = obj["author"] | "";
    book.coverBmpPath = obj["coverBmpPath"] | "";
    if (!book.path.empty() && FinishedBooksStore::add(book)) migrated = true;
  }
  if (migrated || !legacyFinished.isNull()) requestResave();

  LOG_DBG("RBS", "Recent books loaded from file (%d entries)", getCount());
  return true;
}

void RecentBooksStore::addBook(const std::string& path, const std::string& title, const std::string& author,
                               const std::string& coverBmpPath) {
  bool changed = pruneMissing();
  auto it =
      std::find_if(recentBooks.begin(), recentBooks.end(), [&](const RecentBook& book) { return book.path == path; });

  if (it == recentBooks.begin() && it != recentBooks.end() && it->title == title && it->author == author &&
      it->coverBmpPath == coverBmpPath) {
    if (changed) saveToFile();
    return;
  }

  if (it != recentBooks.end()) recentBooks.erase(it);
  recentBooks.insert(recentBooks.begin(), {path, title, author, coverBmpPath});
  if (recentBooks.size() > MAX_RECENT_BOOKS) recentBooks.resize(MAX_RECENT_BOOKS);
  saveToFile();
}

void RecentBooksStore::updateBook(const std::string& path, const std::string& title, const std::string& author,
                                  const std::string& coverBmpPath) {
  auto it =
      std::find_if(recentBooks.begin(), recentBooks.end(), [&](const RecentBook& book) { return book.path == path; });
  if (it == recentBooks.end()) return;
  if (it->title == title && it->author == author && it->coverBmpPath == coverBmpPath) return;
  it->title = title;
  it->author = author;
  it->coverBmpPath = coverBmpPath;
  saveToFile();
}

void RecentBooksStore::markFinished(const std::string& path, const std::string& title, const std::string& author,
                                    const std::string& coverBmpPath) {
  const RecentBook book{path, title, author, coverBmpPath};
  if (!FinishedBooksStore::add(book)) {
    LOG_ERR("RBS", "Failed to persist finished book: %s", path.c_str());
    return;
  }
  removeByPath(path);
}

bool RecentBooksStore::removeFinishedByPath(const std::string& path) {
  return FinishedBooksStore::removeByPath(path);
}

bool RecentBooksStore::isFinished(const std::string& path) const {
  return FinishedBooksStore::contains(path);
}

bool RecentBooksStore::removeByPath(const std::string& path) {
  auto it =
      std::find_if(recentBooks.begin(), recentBooks.end(), [&](const RecentBook& book) { return book.path == path; });
  if (it == recentBooks.end()) return false;
  recentBooks.erase(it);
  if (!saveToFile()) LOG_ERR("RBS", "Failed to persist removal of recent book: %s", path.c_str());
  return true;
}

void RecentBooksStore::updatePath(const std::string& oldPath, const std::string& newPath,
                                  const std::string& oldCachePath, const std::string& newCachePath) {
  bool changed = false;
  auto it = std::find_if(recentBooks.begin(), recentBooks.end(),
                         [&](const RecentBook& book) { return book.path == oldPath; });
  if (it != recentBooks.end()) {
    it->path = newPath;
    if (!oldCachePath.empty() && !it->coverBmpPath.empty() && it->coverBmpPath.rfind(oldCachePath, 0) == 0) {
      it->coverBmpPath = newCachePath + it->coverBmpPath.substr(oldCachePath.size());
    }
    changed = true;
  }
  if (changed) saveToFile();
  FinishedBooksStore::updatePath(oldPath, newPath, oldCachePath, newCachePath);
}

bool RecentBooksStore::isMissing(const RecentBook& book) { return !Storage.exists(book.path.c_str()); }

bool RecentBooksStore::pruneMissing() {
  const size_t before = recentBooks.size();
  recentBooks.erase(std::remove_if(recentBooks.begin(), recentBooks.end(), &isMissing), recentBooks.end());
  return recentBooks.size() != before;
}

RecentBook RecentBooksStore::getDataFromBook(std::string path) const {
  std::string lastBookFileName = "";
  const size_t lastSlash = path.find_last_of('/');
  if (lastSlash != std::string::npos) lastBookFileName = path.substr(lastSlash + 1);

  LOG_DBG("RBS", "Loading recent book: %s", path.c_str());

  if (FsHelpers::hasEpubExtension(lastBookFileName)) {
    Epub epub(path, "/.crosspoint");
    epub.load(false, true);
    return RecentBook{path, epub.getTitle(), epub.getAuthor(), epub.getThumbBmpPath()};
  } else if (FsHelpers::hasXtcExtension(lastBookFileName)) {
    Xtc xtc(path, "/.crosspoint");
    if (xtc.load()) return RecentBook{path, xtc.getTitle(), xtc.getAuthor(), xtc.getThumbBmpPath()};
  } else if (FsHelpers::hasTxtExtension(lastBookFileName) || FsHelpers::hasMarkdownExtension(lastBookFileName)) {
    return RecentBook{path, lastBookFileName, "", ""};
  }
  return RecentBook{path, "", "", ""};
}
