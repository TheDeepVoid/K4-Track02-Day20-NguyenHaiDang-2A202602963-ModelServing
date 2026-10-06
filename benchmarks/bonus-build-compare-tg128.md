# Bonus B1 - Prebuilt vs Build từ Source

Host `Linux-x86_64` · CPU `11th Gen Intel(R) Core(TM) i7-11800H @ 2.30GHz`
Vector extensions: AVX-512, AVX2
llama.cpp `b10488` cả hai phía · `threads=8` ·
**cả hai dùng `ngl=0`** để cô lập yếu tố compiler ·
metric `tg128`, 3 lần lặp

| Binary | Build cho | tg128 (tok/s) | So sánh |
|:--|--:|--:|--:|
| Prebuilt release | Runtime CPU dispatch | 35.9 | 1.00x |
| Source build | CPU này (`-DGGML_NATIVE=ON`) | 33.5 | 0.93x |

Trên máy này, **prebuilt nhanh hơn 1.07×**.

```
before:  35.9 tok/s  (prebuilt release)
after:   33.5 tok/s  (source build, -DGGML_NATIVE=ON)
speedup: 0.93x  (source build thua)
```

Cùng source revision, cùng model, cùng backend, cùng `-ngl` — điểm khác duy nhất là compiler được phép giả định gì về CPU.

## Giải thích

Kết quả ngược kỳ vọng: source build với `-DGGML_NATIVE=ON` chậm hơn prebuilt 7%. Có hai cơ chế giải thích điều này:

**1. Prebuilt dùng runtime CPU dispatch với kernel viết tay theo microarch.**
Từ khoảng build b10429 trở đi, llama.cpp không còn ship một binary duy nhất — thay vào đó GGML CPU backend được tách thành nhiều shared library riêng cho từng microarchitecture: `libggml-cpu-icelake.so`, `libggml-cpu-cascadelake.so`, `libggml-cpu-avx2.so`, v.v. Khi khởi động, llama.cpp đọc CPUID flags và `dlopen()` đúng thư viện phù hợp nhất. Với i7-11800H (Tiger Lake / Icelake), dispatcher chọn kernel đã được viết tay và tune cho chính microarch đó — bao gồm kiểm soát thủ công prefetch distance, cache line alignment và loop unrolling cho các shape matmul mà llama.cpp sử dụng.

**2. Workload này bị giới hạn bởi memory bandwidth, không phải instruction throughput.**
Decode (tg128) yêu cầu load toàn bộ ~497 MB model weights từ DRAM cho mỗi token sinh ra. Khi bottleneck là DRAM bandwidth, việc compiler có dùng AVX-512 hay AVX2 không quan trọng — CPU đang idle chờ data, không phải chờ execute instructions. Trong trường hợp này, `-DGGML_NATIVE=ON` không mang lại lợi ích thực sự.

Điểm tinh tế hơn: compiler với `-march=native` auto-vectorize toàn bộ code, nhưng cost model của compiler không được calibrate cho các shape matmul cụ thể của llama.cpp (đặc biệt là decode batch N=1 với ma trận rất mỏng). Code do compiler sinh ra đôi khi tăng memory traffic qua scatter/gather không cần thiết hoặc load rộng hơn mức cần, làm cache evict nhiều hơn thay vì tiết kiệm. Kernel viết tay kiểm soát điều này một cách tường minh — nên thắng trên memory-bound workload dù về FLOPS thì tương đương.

**Kết luận thực tế:** với hardware có AVX-512 và workload decode memory-bound, dùng prebuilt release là lựa chọn đúng. Source build với `-DGGML_NATIVE=ON` chỉ đáng thử trên hardware không có prebuilt phù hợp (ARM không phổ biến, RISC-V) hoặc khi profiling cho thấy bottleneck thực sự là instruction throughput (prefill dài trên GPU, batch lớn).
