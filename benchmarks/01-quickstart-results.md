# 01 - Measure: latency baseline

Model `Qwen3.5 0.8B` · host `Linux-x86_64` · llama.cpp `b10488`
Settings: `threads=8` `ngl=0` `ctx=2048`
`max_tokens=64` · warm-up discarded
Completed requests: `Q4_K_M` 10/10 · `UD-Q2_K_XL` 10/10

| Quantization | Size (GB) | Load (ms) | TTFT P50/P95 (ms) | TPOT P50/P95 (ms) | E2E P50/P95/P99 (ms) | Decode (tok/s) |
|:--|--:|--:|--:|--:|--:|--:|
| Q4_K_M | 0.50 | 1047 | 106 / 118 | 18.5 / 19.5 | 1269 / 1348 / 1348 | 54.0 |
| UD-Q2_K_XL | 0.39 | 1034 | 166 / 199 | 16.6 / 17.1 | 1193 / 1279 / 1279 | 60.3 |

- **TTFT** = prefill. Prompt ngắn giữ TTFT nhỏ; RAG context dài là nơi nó bùng nổ.
- **TPOT** = chi phí decode mỗi token đầu ra, bị giới hạn bởi memory bandwidth. `decode tok/s = 1000 / TPOT_p50`.
- `UD-Q2_K_XL` decode **nhanh hơn 1.12×** so với `Q4_K_M`, nhỏ hơn 0.11 GB.

## Nhận xét

UD-Q2_K_XL decode nhanh hơn 1.12× (60.3 vs 54.0 tok/s) và load trong thời gian tương đương (~1034 ms vs ~1047 ms), nhưng TTFT chậm hơn rõ rệt: 166 ms P50 so với 106 ms — tức chậm hơn 57% ở bước prefill. Điều này hợp lý: ít bit hơn đồng nghĩa bước dequantize trong prefill tốn thêm compute so với lượng compute tiết kiệm được ở decode. Trên máy này (CPU-only, AVX-512), decode bị giới hạn bởi memory bandwidth nên đóng gói weights chặt hơn trực tiếp giảm số bytes phải truyền mỗi token — đó là lợi thế. Với inference context ngắn, penalty TTFT chấp nhận được; với RAG context dài, penalty TTFT tích lũy và sẽ ảnh hưởng latency cảm nhận của người dùng nhiều hơn lợi ích decode mang lại. Quant UD ("Unsloth Dynamic") giữ các layer nhạy cảm ở precision cao hơn nên chất lượng trả lời vẫn dùng được — model vẫn trả lời đúng các câu hỏi thực tế — nhưng các bước suy luận tinh tế hơn cho thấy sai lệch nhỏ hơn so với Q4_K_M. Kết luận: với workload chat latency-sensitive, prompt ngắn, UD-Q2_K_XL đáng dùng. Với RAG pipeline context dài thì không.
