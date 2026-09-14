#pragma once
#include <ArduinoJson.h>
#include <PersistableStore.h>

#include <string>
#include <vector>

struct RecentBook {
  std::string path;
  std::string title;
  std::string author;
  std::string coverBmpPath;

  bool operator==(const RecentBook& other) const { return path == other.path; }
};

class RecentBooksStore : public PersistableStore<RecentBooksStore> {
 private:
  std::vector<RecentBook> recentBooks;
  std::vector<RecentBook> finishedBooks;

  static constexpr int MAX_RECENT_BOOKS = 10;
  static constexpr int MAX_FINISHED_BOOKS = 100;

  RecentBooksStore() = default;
  ~RecentBooksStore() = default;

  friend class PersistableStore<RecentBooksStore>;

 public:
  static const char* getFilePath() { return "/.crosspoint/recent.json"; }
  void toJson(JsonDocument& doc) const;
  bool fromJson(JsonVariantConst doc);

  void addBook(const std::string& path, const std::string& title, const std::string& author,
               const std::string& coverBmpPath);
  void updateBook(const std::string& path, const std::string& title, const std::string& author,
                  const std::string& coverBmpPath);
  void markFinished(const std::string& path, const std::string& title, const std::string& author,
                    const std::string& coverBmpPath);
  bool removeByPath(const std::string& path);
  bool removeFinishedByPath(const std::string& path);
  bool isFinished(const std::string& path) const;
  void updatePath(const std::string& oldPath, const std::string& newPath, const std::string& oldCachePath,
                  const std::string& newCachePath);
  static bool isMissing(const RecentBook& book);
  bool pruneMissing();

  const std::vector<RecentBook>& getBooks() const { return recentBooks; }
  const std::vector<RecentBook>& getFinishedBooks() const { return finishedBooks; }
  int getCount() const { return static_cast<int>(recentBooks.size()); }
  int getFinishedCount() const { return static_cast<int>(finishedBooks.size()); }
  RecentBook getDataFromBook(std::string path) const;
};

#define RECENT_BOOKS RecentBooksStore::getInstance()
