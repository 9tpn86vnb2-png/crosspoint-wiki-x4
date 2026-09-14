#pragma once

#include <cstdint>
#include <string>
#include <vector>

struct RecentBook;

struct FinishedBooksCatalog {
  static constexpr uint32_t CHECKPOINT_STRIDE = 32;
  uint32_t count = 0;
  std::vector<uint32_t> checkpoints;

  void clear() {
    count = 0;
    checkpoints.clear();
  }
};

class FinishedBooksStore {
 public:
  static constexpr const char* FILE_PATH = "/.crosspoint/finished-books.dat";

  static bool add(const RecentBook& book);
  static bool contains(const std::string& path);
  static bool removeByPath(const std::string& path);
  static bool updatePath(const std::string& oldPath, const std::string& newPath,
                         const std::string& oldCachePath, const std::string& newCachePath);

  static bool buildCatalog(FinishedBooksCatalog& catalog);
  static bool loadNewestWindow(const FinishedBooksCatalog& catalog, uint32_t firstNewest,
                               uint16_t count, std::vector<RecentBook>& out);
};
