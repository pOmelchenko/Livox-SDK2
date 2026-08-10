#include <cstdint>

int main() {
  alignas(std::uint32_t) std::uint8_t storage[sizeof(std::uint32_t) + 1] = {};
  const volatile std::uint32_t value =
      *reinterpret_cast<const std::uint32_t*>(storage + 1);
  return value == 0xFFFFFFFFu ? 1 : 0;
}
