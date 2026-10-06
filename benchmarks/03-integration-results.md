# 03 - Tích Hợp: Chạy RAG Pipeline

Host `Linux-x86_64` · llama.cpp `b10488` ·
retrieval backend: **keyword overlap** · 3 câu hỏi

| Câu hỏi | Contexts lấy được | embed (ms) | retrieve (ms) | llm (ms) | total (ms) |
|:--|--:|--:|--:|--:|--:|
| Why is goodput more useful than raw throughp... | goodput, paged, radix | 0.0 | 0.0 | 2767.8 | 2767.9 |
| What problem does PagedAttention actually so... | paged, radix, disagg | 0.0 | 0.0 | 1792.7 | 1792.7 |
| When does splitting prefill and decode help?... | disagg, radix, batching | 0.0 | 0.0 | 2110.4 | 2110.5 |

Trung bình mỗi stage (ms): embed **0.0** · retrieve **0.0** ·
llm **2223.6** · total **2223.7**
Stage chiếm nhiều nhất: **llm** (100% tổng)

## Câu trả lời trả về

**Tại sao goodput hữu ích hơn raw throughput?**

> Goodput hữu ích hơn vì raw throughput bỏ qua SLO. Goodput chỉ đếm request/giây đáp ứng được TTFT và TPOT target — throughput ở điểm bão hòa tăng chậm trong khi latency tăng nhanh, nên raw throughput không phản ánh trải nghiệm thực của người dùng.

**PagedAttention giải quyết vấn đề gì?**

> PagedAttention giải quyết **internal fragmentation** trong GPU memory. Nó lưu KV cache trong các trang không liên tục (non-contiguous pages) — tương tự virtual memory trong OS — thay vì yêu cầu block liên tục. Điều này loại bỏ phần lớn waste memory thường thấy với allocation kiểu cũ.

**Khi nào tách prefill và decode mang lại lợi ích?**

> Khi prefill là compute-bound và decode là memory-bound. Tách hai workload này ra hai pool riêng cho phép mỗi pool được tối ưu theo đúng bottleneck của nó — không còn tình trạng prefill dài chiếm device và stall decode của các request khác.

## Các phần N16–N19 nào là thật

| Day | Phần | Thật hay stub? |
|---|---|---|
| N16 Cloud/IaC | infrastructure / deployment | stub — chạy hoàn toàn local |
| N17 Data pipeline | ingestion / chunking | stub — documents là hardcoded strings trong pipeline.py |
| N18 Lakehouse | storage / retrieval store | stub — không có vector DB; dùng keyword-overlap fallback |
| N19 Vector + features | embedding + ANN search | stub — embed stage trả về 0 ms (không load embedding model) |
| N20 Serving | `llama-server` | thật — OpenAI-compat endpoint trên :8080 |

Stage llm chiếm 100% là kết quả kỳ vọng: embed và retrieve đều stub về 0 ms nên toàn bộ thời gian nằm ở decode loop. Ngay cả với embedding model thật, llm vẫn sẽ dominate — trên CPU ~54 tok/s, sinh 100 token tốn ~1.8 s, trong khi model embed nhỏ (all-MiniLM-L6-v2) embed một đoạn 256 token dưới 10 ms. Để giảm latency pipeline 2×, tôi sẽ tấn công stage llm trước: tăng `--parallel` (giảm queue depth), hoặc chuyển sang UD-Q2_K_XL (nhanh hơn 1.12×), hoặc giảm max_tokens từ 128 xuống 64 — đủ cho câu trả lời RAG một đoạn ngắn mà không cần thay đổi model.
