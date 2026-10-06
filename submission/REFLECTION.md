# Reflection — Day 20 Lab (Personal Report)

> **Đây là báo cáo cá nhân.** Số liệu của bạn **không** so sánh được với bạn cùng lớp
> — chỉ so **before vs after trên chính máy bạn**. Rubric chấm độ rõ ràng của setup,
> đo lường và **lập luận**, không chấm tốc độ tuyệt đối.
>
> `make verify` sẽ fail nếu còn placeholder chưa điền. Đó là cố ý.

**Họ Tên:** Nguyễn Hải Đăng
**MSSV:** 2A202602963
**Cohort:** K4-Track02
**Ngày submit:** 2026-10-06

---

## 1. Hardware & runtime  *(rubric 1, 2 — 10 điểm)*

> Từ `make probe`. Paste output hoặc điền tay.

- **OS:** Linux CachyOS (kernel 7.2.9-1-cachyos, x86_64)
- **CPU:** 11th Gen Intel Core i7-11800H @ 2.30 GHz
- **Cores:** 8 physical / 16 logical
- **CPU extensions:** AVX2, AVX-512
- **RAM:** 15.3 GB
- **Accelerator:** NVIDIA GeForce RTX 3060 Laptop GPU (6144 MiB) — dùng CPU-only runtime (ngl=0) vì prebuilt CUDA build cho b10488 không tồn tại trên GitHub releases
- **llama.cpp asset đã tải:** `llama-b10488-bin-ubuntu-x64.tar.gz` (CPU/AVX-512 build)
- **Model đã dùng:** Qwen3.5 0.8B (`LAB_MODEL=qwen35-0.8b`)
- **Quantization:** Q4_K_M (primary) + UD-Q2_K_XL (compare)

**Chạy ở đâu:** laptop của tôi

**Setup story:** Hai bước cần workaround. Thứ nhất, `fetch-runtime.py` tải về `llama-b10488-bin-ubuntu-vulkan-x64.tar.gz` nhưng bị corrupted và tarball vulkan/CPU trộn lẫn gây SIGBUS — phải tải lại `ubuntu-x64` bằng wget và xoá `libggml-vulkan.so` thừa. Thứ hai, hai file `.gguf` tải từ hf-mirror bị truncated (199 MB thay vì 508 MB); phải dùng `huggingface_hub.hf_hub_download` trực tiếp để lấy đúng file.

---

## 2. Đo lường  *(rubric 3, 4, 5 — 20 điểm)*

> Paste bảng từ `benchmarks/01-quickstart-results.md` (`make bench` tự sinh).

| Quantization | Size (GB) | Load (ms) | TTFT P50/P95 (ms) | TPOT P50/P95 (ms) | E2E P50/P95/P99 (ms) | Decode (tok/s) |
|---|--:|--:|--:|--:|--:|--:|
| Q4_K_M | 0.50 | 1047 | 106 / 119 | 18.5 / 19.5 | 1269 / 1349 / 1349 | 54.0 |
| UD-Q2_K_XL | 0.39 | 1034 | 166 / 199 | 16.6 / 17.2 | 1193 / 1279 / 1279 | 60.3 |

**Quan sát:** UD-Q2_K_XL decode nhanh hơn 1.12× (60.3 vs 54.0 tok/s) nhờ ít bytes hơn phải stream từ RAM — decode bị giới hạn bởi memory bandwidth, không phải FLOPs. Tuy nhiên TTFT chậm hơn 57% (166 ms vs 106 ms) vì dequantize trong bước prefill tốn thêm compute. Trên máy này (CPU-only, short prompts), UD-Q2_K_XL đáng dùng: tốc độ tốt hơn và chất lượng trả lời vẫn coherent cho các câu hỏi factual. Với RAG context dài, TTFT penalty sẽ thấy rõ hơn.

---

## 3. Serving under load  *(rubric 8, 9, 10 — 20 điểm)*

> Từ `benchmarks/02-server-results.md` (`make load-report`).

| Users | RPS | P50 (ms) | P95 (ms) | P99 (ms) | Eff. concurrency | Failures |
|--:|--:|--:|--:|--:|--:|--:|
| 10 | 1.63 | 4700 | 9500 | 12000 | 8.5 | 0.0% |
| 50 | 1.73 | 26000 | 31000 | 32000 | 37.4 | 0.0% |

- **Offered load tăng 5×, throughput thực tăng:** 1.07×
- **P95 tăng:** 3.26×
- **Effective concurrency ở 50 users:** 37.4 so với `--parallel` = 4 slots

**Peak `llamacpp:n_busy_slots_per_decode`**: 4.00 / 4 slots (100%)

**Saturation reading:** Server bão hoà trước khi đạt 50 users — con số thuyết phục là effective concurrency 37.4 với chỉ 4 decode slots, tức occupancy ratio 9.35×. Throughput tăng 1.07× trong khi P95 tăng 3.26× chứng tỏ load thêm biến thành queue time chứ không phải compute time (compute time không thay đổi — slot vẫn xử lý ~54 tok/s). Knob đầu tiên cần nâng là `--parallel`: tăng từ 4 lên 8 doubles điểm vào hàng mà không cần thêm hardware, vì mỗi slot Qwen3.5 0.8B ở ctx=512 chỉ cần ~50 MB KV cache — hoàn toàn nằm trong 15 GB RAM.

---

## 4. Integration  *(rubric 12, 13 — 15 điểm)*

> Từ `make pipeline`. Nói thật cái nào real, cái nào stub — stub **không** mất điểm.

| Day | Piece | Real hay stub? |
|---|---|---|
| N16 Cloud/IaC | infrastructure / deployment | stub — chạy hoàn toàn local |
| N17 Data pipeline | ingestion / chunking | stub — documents là hardcoded strings trong pipeline.py |
| N18 Lakehouse | storage / retrieval store | stub — không có vector DB; dùng keyword-overlap fallback |
| N19 Vector + features | embedding + ANN search | stub — embed stage trả về 0 ms (không load embedding model) |
| N20 Serving | `llama-server` | real |

**Latency split** (mean của 3 query, từ output của `pipeline.py`):

- embed: 0.0 ms
- retrieve: 0.0 ms
- llm: 2223.6 ms
- **stage chiếm nhiều nhất:** llm (100% của total)

**Reflection:** Bottleneck là LLM decode — hoàn toàn đúng kỳ vọng vì embed và retrieve đều bị stub. Ngay cả với embedding model thật, LLM vẫn chiếm 95%+ tổng latency ở tốc độ ~54 tok/s CPU-only. Để giảm latency 2×, tôi sẽ tấn công stage llm trước: giảm max_tokens (128 → 64) hoặc dùng UD-Q2_K_XL (60.3 tok/s), hai bước này không cần thêm phần cứng.

---

## 5. The single change that mattered most  *(rubric 11 — 10 điểm)*

> **Phần quan trọng nhất của report.** Không cần bonus track: `make tune` đã cho bạn
> một before/after thật (`benchmarks/01-tuning-tg128.md`). Đổi quantization,
> `LAB_N_CTX`, hay `--parallel` rồi đo lại cũng được.

**Change:** tăng `-t` từ 1 lên 8 (physical core count) — từ kết quả `make tune`

```
before:  21.0 tok/s  (-t 1)
after:   56.5 tok/s  (-t 8)
speedup: 2.69×
```

**Tại sao nó work:**

Decode của LLM bị giới hạn bởi **memory bandwidth**, không phải FLOPs. Mỗi token được generate yêu cầu load toàn bộ weights của model (~508 MB cho Q4_K_M) từ DRAM vào L1/L2 cache của CPU — một lần per token, bất kể prompt dài hay ngắn. Trên i7-11800H, mỗi physical core có kênh memory riêng; khi chạy `-t 1` chỉ có 1 core đang kéo data nên toàn bộ bandwidth của 4-channel DDR4 bị bỏ phí. Tăng lên 8 physical cores đồng nghĩa 8 luồng cùng kéo song song, tổng bandwidth tăng gần tuyến tính → throughput tăng 2.69×.

Kết quả tại -t 8 là **best** (56.5 tok/s) và sau đó giảm mạnh: -t 16 = 38.7 tok/s, -t 32 = 22.3 tok/s. Đây là hành vi kỳ vọng: hyperthreads (-t 16) chia sẻ cùng physical core và cùng L2 cache, nên không thêm bandwidth — thay vào đó chúng tranh nhau cache lines của nhau, gây cache thrash và làm chậm lại. Tại -t 32 (oversubscription 2× logical), OS scheduler thêm context-switch overhead và latency càng tăng. Knee chính xác tại physical core count (8) xác nhận rằng bottleneck là memory bandwidth, không phải compute hay scheduling.

---

## 6. Bonus  *(optional — tối đa 10 điểm)*

> Bỏ trống nếu không làm. Xem `docs/bonus/README.md`. Đừng làm hết — **một** finding sâu
> ăn điểm hơn năm bảng nông.

**Đã làm:** B1 build-compare · B2 sweep-quant + sweep-ctx + sweep-batch · B3 before/after · B4 C2 KV-cache quant · B5 C9 embedding serving (real mode) + C8 semantic cache (real mode)

**Numbers (B2 quant sweep — finding tốt nhất):**

```
before:  20.2 tok/s  (UD-Q4_K_XL, prebuilt benchmark)
after:   59.3 tok/s  (UD-Q2_K_XL)
speedup: 2.93×
```

**Điều này nói lên gì mà deck chưa nói:**

Deck dạy rằng "ít bit hơn = nhanh hơn vì memory-bandwidth-bound". Sweep này xác nhận điều đó, nhưng còn tiết lộ một điểm không rõ trong slide: **cùng một số bit, định dạng quant khác nhau cho kết quả khác nhau đáng kể**. UD-Q4_K_XL (20.2 tok/s) chậm hơn Q4_K_M (54.0 tok/s) mặc dù đều là "4-bit". Lý do: UD (Unsloth Dynamic) giữ các layer nhạy cảm ở precision cao hơn — effective bytes/weight cao hơn flat Q4_K_M, nên băng thông phải tải nhiều hơn mỗi token. Khi chọn quant để deploy, không thể chỉ nhìn số bit — phải đo tốc độ thực tế trên hardware của mình.

B1 build-compare tiết lộ thêm: prebuilt (35.9 tok/s) nhanh hơn source `-DGGML_NATIVE=ON` (33.5 tok/s). Trên machine memory-bandwidth-bound, compiler SIMD optimization không giúp nhiều — prebuilt thắng nhờ runtime CPU dispatch chọn kernel được viết tay cho Tiger Lake, trong khi GCC auto-vectorization tạo ra code generic hơn.

---

## 7. Điều làm bạn ngạc nhiên nhất  *(optional)*

Điều ngạc nhiên nhất là `-t 8` (physical cores) vượt `-t 4` rõ rệt (56.5 vs 53.1 tok/s) trong khi lý thuyết băng thông memory thường cho curve phẳng sau physical/2. Lý do là i7-11800H dùng DDR4 dual-channel với interleaving tốt — 8 threads khai thác đủ cả hai channel và hardware prefetcher vẫn hoạt động; chỉ đến hyperthreads mới thấy cache thrash rõ.

---

## 8. Self-check trước khi push

- [x] `hardware.json` committed
- [x] `models/active.json` committed
- [x] `benchmarks/01-quickstart-results.md` committed (`make bench`)
- [x] `benchmarks/01-tuning-tg128.md` committed (`make tune`)
- [x] `benchmarks/02-server-results.md` committed (`make load-report`)
- [x] `benchmarks/02-server-batching-u50.md` hoặc `-metrics-u50.csv` committed (`make metrics`)
- [x] `benchmarks/locust-10_stats.csv` + `locust-50_stats.csv` committed (`make load-10` / `load-50`)
- [x] `benchmarks/03-integration-results.md` committed (`make pipeline`)
- [x] Mọi section **"required — replace this line"** trong các file `benchmarks/*.md`
      đã được thay bằng nhận xét của bạn
- [x] 5 screenshots trong `submission/screenshots/`
- [x] `make verify` → **exit 0**
- [x] Repo tên đúng mẫu `K4-L3-DAY20-HoVaTen-MSSV-ModelServing` (xem `docs/SUBMISSION.md`)
- [x] Repo GitHub ở chế độ **public**
- [x] Đã push và paste public URL vào VinUni LMS **trước 23:59 (UTC+7) ngày làm lab**
- [x] **Không** commit `models/*.gguf`, `runtime/` hay `.env` (đã có trong `.gitignore`)

**Quan trọng:** repo phải **public** đến khi điểm được công bố. Private → grader không
xem được → 0 điểm.

---

## 9. Khai báo sử dụng AI  *(xem `docs/RULES.md` §3)*

Dùng AI (ChatGPT / Kiro) để tra cứu khái niệm (TTFT, TPOT, Little's Law, memory-bandwidth bottleneck) và gợi ý cú pháp lệnh khi bị stuck. Toàn bộ số liệu đo được, nhận xét và lập luận trong report là của bản thân sau khi chạy thực tế trên máy.
