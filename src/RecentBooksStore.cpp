#include "RecentBooksStore.h"

#include <Epub.h>
#include <FsHelpers.h>
#include <HalStorage.h>
#include <Logging.h>
#include <Xtc.h>

#include <algorithm>
#include <iterator>

namespace {
RecentBook bookFromJson(JsonObjectConst obj) {
  RecentBook book;
  book.path = obj["path"] | "";
  book.title = obj["title"] | "";
  book.author = obj["author"] | "";
  book.coverBmpPath = obj["coverBmpPath"] | "";
  return book;
}

void bookToJson(JsonArray arr, const RecentBook& book) {
  JsonObject obj = arr.add<JsonObject>();
  obj["path"] = book.path;
  obj["title"] = book.title;
  obj["author"] = book.author;
  obj["coverBmpPath"] = book.coverBmpPath;
}
}  // namespace

void RecentBooksStore::toJson(JsonDocument& doc) const {
  JsonArray arr = doc["books"].to<JsonArray>();
  for (const auto& book : recentBooks) bookToJson(arr, book);

  JsonArray finished = doc["finished"].to<JsonArray>();
  for (const auto& book : finishedBooks) bookToJson(finished, book);
}

bool RecentBooksStore::fromJson(JsonVariantConst doc) {
  recentBooks.clear();
  JsonArrayConst arr = doc["books"].as<JsonArrayConst>();
  recentBooks.reserve(std::min(arr.size(), static_cast<size_t>(MAX_RECENT_BOOKS)));
  for (JsonObjectConst obj : arr) {
    if (getCount() >= MAX_RECENT_BOOKS) break;
    recentBooks.push_back(bookFromJson(obj));
  }

  finishedBooks.clear();
  JsonArrayConst finished = doc["finished"].as<JsonArrayConst>();
  finishedBooks.reserve(std::min(finished.size(), static_cast<size_t>(MAX_FINISHED_BOOKS)));
  for (JsonObjectConst obj : finished) {
    if (getFinishedCount() >= MAX_FINISHED_BOOKS) break;
    finishedBooks.push_back(bookFromJson(obj));
  }

  LOG_DBG("RBS", "Recent books loaded (%d recent, %d finished)", getCount(), getFinishedCount());
  return true;
}

void RecentBooksStore::addBook(const std::string& path, const std::string& title, const std::string& author,
                               const std::string& coverBmpPath) {
  pruneMissing();

  auto it =
      std::find_if(recentBooks.begin(), recentBooks.end(), [&](const RecentBook& book) { return book.path == path; });
  if (it != recentBooks.end()) recentBooks.erase(it);

  recentBooks.insert(recentBooks.begin(), {path, title, author, coverBmpPath});
  if (recentBooks.size() > MAX_RECENT_BOOKS) recentBooks.resize(MAX_RECENT_BOOKS);
  saveToFile();
}

void RecentBooksStore::updateBook(const std::string& path, const std::string& title, const std::string& author,
                                  const std::string& coverBmpPath) {
  auto update = [&](std::vector<RecentBook>& books) {
    auto it = std::find_if(books.begin(), books.end(), [&](const RecentBook& book) { return book.path == path; });
    if (it == books.end()) return false;
    it->title = title;
    it->author = author;
    it->coverBmpPath = coverBmpPath;
    return true;
  };
  if (update(recentBooks) || update(finishedBooks)) saveToFile();
}

void RecentBooksStore::markFinished(const std::string& path, const std::string& title, const std::string& author,
                                    const std::string& coverBmpPath) {
  recentBooks.erase(
      std::remove_if(recentBooks.begin(), recentBooks.end(), [&](const RecentBook& book) { return book.path == path; }),
      recentBooks.end());

  auto it =
      std::find_if(finishedBooks.begin(), finishedBooks.end(), [&](const RecentBook& book) { return book.path == path; });
  if (it != finishedBooks.end()) {
    it->title = title;
    it->author = author;
    it->coverBmpPath = coverBmpPath;
  } else {
    finishedBooks.insert(finishedBooks.begin(), {path, title, author, coverBmpPath});
    if (finishedBooks.size() > MAX_FINISHED_BOOKS) finishedBooks.resize(MAX_FINISHED_BOOKS);
  }
  saveToFile();
}

bool RecentBooksStore::removeByPath(const std::string& path) {
  auto it =
      std::find_if(recentBooks.begin(), recentBooks.end(), [&](const RecentBook& book) { return book.path == path; });
  if (it == recentBooks.end()) return false;
  recentBooks.erase(it);
  if (!saveToFile()) LOG_ERR("RBS", "Failed to persist recent removal: %s", path.c_str());
  return true;
}

bool RecentBooksStore::removeFinishedByPath(const std::string& path) {
  auto it = std::find_if(finishedBooks.begin(), finishedBooks.end(),
                         [&](const RecentBook& book) { return book.path == path; });
  if (it == finishedBooks.end()) return false;
  finishedBooks.erase(it);
  if (!saveToFile()) LOG_ERR("RBS", "Failed to persist finished removal: %s", path.c_str());
  return true;
}

bool RecentBooksStore::isFinished(const std::string& path) const {
  return std::any_of(finishedBooks.begin(), finishedBooks.end(),
                     [&](const RecentBook& book) { return book.path == path; });
}

void RecentBooksStore::updatePath(const std::string& oldPath, const std::string& newPath,
                                  const std::string& oldCachePath, const std::string& newCachePath) {
  bool changed = false;
  auto update = [&](std::vector<RecentBook>& books) {
    auto it = std::find_if(books.begin(), books.end(), [&](const RecentBook& book) { return book.path == oldPath; });
    if (it == books.end()) return;
    it->path = newPath;
    if (!oldCachePath.empty() && !it->coverBmpPath.empty() && it->coverBmpPath.rfind(oldCachePath, 0) == 0) {
      it->coverBmpPath = newCachePath + it->coverBmpPath.substr(oldCachePath.size());
    }
    changed = true;
  };
  update(recentBooks);
  update(finishedBooks);
  if (changed) saveToFile();
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
