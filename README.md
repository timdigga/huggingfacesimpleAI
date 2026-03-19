<div align="center">

<img src="https://capsule-render.vercel.app/api?type=venom&color=0:ff6b6b,25:ffd93d,50:6bcb77,75:4d96ff,100:c77dff&height=200&section=header&text=Tim's%20AI&fontSize=90&fontColor=ffffff&fontAlignY=55&desc=Local%20Coding%20Assistant%20%E2%80%94%20no%20cloud%2C%20no%20BS&descSize=18&descAlignY=78&animation=fadeIn" width="100%"/>

</div>

<div align="center">

<img src="https://readme-typing-svg.demolab.com?font=JetBrains+Mono&weight=700&size=20&pause=800&color=FF6B6B&center=true&vCenter=true&width=700&lines=runs+on+YOUR+machine+%F0%9F%92%BB;swap+models+without+restarting+%F0%9F%94%A5;streams+tokens+live+as+they+generate+%E2%9A%A1;syntax+highlighting+out+of+the+box+%F0%9F%8E%A8;your+code+never+leaves+your+desk+%F0%9F%94%92" alt="typing" />

<br/><br/>

![Python](https://img.shields.io/badge/Python_3.10+-FFD93D?style=for-the-badge&logo=python&logoColor=333)
![PyTorch](https://img.shields.io/badge/PyTorch-FF6B6B?style=for-the-badge&logo=pytorch&logoColor=white)
![HuggingFace](https://img.shields.io/badge/🤗_Transformers-6BCB77?style=for-the-badge&logoColor=white)
![Tkinter](https://img.shields.io/badge/Tkinter_GUI-4D96FF?style=for-the-badge&logo=python&logoColor=white)
![CUDA](https://img.shields.io/badge/CUDA_Ready-C77DFF?style=for-the-badge&logo=nvidia&logoColor=white)
![MIT](https://img.shields.io/badge/License-MIT-FF6B6B?style=for-the-badge)

</div>

---

## 👋 What's this?

A **desktop coding assistant** I built that runs entirely on your own hardware. Pick any model off HuggingFace, load it up, and start chatting — with real streaming output, syntax-highlighted code blocks, copy buttons on every snippet, and optional text-to-speech. No API key. No monthly bill. No data going anywhere.

It's got a full Tkinter UI with a dark green terminal vibe, a model manager where you can hot-swap models without restarting, and generation sliders so you can actually tune what the AI does.

---

## 🎨 Features

<table>
<tr>
<td width="50%" valign="top">

### 🔴 &nbsp;Model Control
- Hot-swap **any HuggingFace model** at runtime
- Persistent model registry with load counts & timestamps
- Auto-detects **CUDA or CPU** — works on both
- `torch.compile` acceleration on PyTorch 2.x
- KV-cache enabled for big CPU speed gains

</td>
<td width="50%" valign="top">

### 🟡 &nbsp;Generation Tuning
- **Temperature** slider — creative vs deterministic
- **Top-p** nucleus sampling
- **Max tokens** — 64 to 4096
- **Repetition penalty** — stop the AI repeating itself
- Stop generation **mid-stream** at any point

</td>
</tr>
<tr>
<td width="50%" valign="top">

### 🟢 &nbsp;The UI
- Live **streaming tokens** — watch it type in real time
- **Syntax highlighting** for Python, JS, TS, Rust, Go, SQL, HTML...
- ⎘ **Copy button on every code block**
- Attach **code files** directly into context (up to 32k chars)
- **Save full conversations** to Markdown
- Mono / prose input toggle, live char + token counter

</td>
<td width="50%" valign="top">

### 🔵 &nbsp;System Prompts
Five built-in presets you can switch instantly:

- 🤖 General Coding Assistant
- 🔍 Code Reviewer
- 🐍 Python Expert
- 🐛 Debugging Assistant
- 🏗️ Architecture & Design

...or write your own in the text box.

</td>
</tr>
</table>

---

## 🚀 Getting started

```bash
git clone https://github.com/timdigga/tims-ai.git
cd huggingfacesimpleAI

python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate

pip install torch transformers pyttsx3
python main_init.py
```

> On first run it'll pull down the default model (`Foundation-Sec-8B-Instruct`) from HuggingFace. Grab a coffee — it's a few GB.

No CUDA? No problem. It falls back to CPU automatically and uses bfloat16 + MKL-DNN for decent performance on modern chips.

---

## 🤖 Compatible HuggingFace Models

Every model below loads with a single paste into the **Model Manager → Add** box. They're grouped by what they're actually good at — pick the one that fits your workflow.

> 💡 **Tip:** All models marked `Instruct` or `Chat` work out of the box with the chat template. Base models won't follow instructions without fine-tuning.

---

### 🛡️ Security & Cybersecurity

These are trained or fine-tuned specifically on security data — CVEs, threat intel, MITRE ATT&CK, compliance frameworks, pen testing concepts. Great if you're doing security work or writing defensive code.

| Model | Repo ID | What it's for |
|---|---|---|
| 🏆 Foundation-Sec-8B-Instruct *(default)* | `fdtn-ai/Foundation-Sec-8B-Instruct` | Cisco's security-specialized Llama 3.1 8B — threat intel, CVEs, NIST, GDPR, SOC work |
| 🧠 Foundation-Sec-8B-Reasoning | `fdtn-ai/Foundation-Sec-8B-Reasoning` | Same model but with chain-of-thought reasoning — slower, more thorough security analysis |
| 🔐 ZySec-7B | `ZySec-AI/SecurityLLM` | Fine-tuned for SOC teams — attack surfaces, cloud security, incident handling, compliance |

---

### 💻 Code-First Models

Built specifically to write, explain, debug, and complete code. These beat general models on most coding benchmarks.

| Model | Repo ID | What it's for |
|---|---|---|
| 🚀 DeepSeek-Coder-V2-Lite-Instruct | `deepseek-ai/DeepSeek-Coder-V2-Lite-Instruct` | 16B MoE model — one of the best open code models, especially for complex multi-file tasks |
| 💻 DeepSeek Coder 6.7B | `deepseek-ai/deepseek-coder-6.7b-instruct` | Compact, fast code model — great for everyday coding on CPU |
| 🦙 CodeLlama 7B Instruct | `codellama/CodeLlama-7b-Instruct-hf` | Meta's dedicated code model — solid Python, C++, Java support |
| 🦙 CodeLlama 13B Instruct | `codellama/CodeLlama-13b-Instruct-hf` | Larger CodeLlama — noticeably better at longer functions and explanations |
| 🦙 CodeLlama 34B Instruct | `codellama/CodeLlama-34b-Instruct-hf` | Heavy hitter — needs a good GPU but competes with GPT-3.5 on code |
| 🧩 Qwen2.5-Coder-7B-Instruct | `Qwen/Qwen2.5-Coder-7B-Instruct` | Alibaba's code specialist — strong across 40+ languages, excellent completions |
| 🧩 Qwen2.5-Coder-14B-Instruct | `Qwen/Qwen2.5-Coder-14B-Instruct` | Bigger Qwen coder — competes with much larger models on HumanEval |
| ⭐ Qwen3-Coder-8B-Instruct | `Qwen/Qwen3-Coder-8B-Instruct` | Latest Qwen coder, 2025 — strong agentic coding and tool-calling support |
| 🎯 Codestral-22B | `mistralai/Codestral-22B-v0.1` | Mistral's code model — supports 80+ languages, great fill-in-the-middle |
| 🔷 StarCoder2-15B-Instruct | `bigcode/starcoder2-15b-instruct-v0.1` | BigCode's instruction-tuned star — trained on 600+ programming languages |
| 🏗️ IBM Granite 8B Code Instruct | `ibm-granite/granite-8b-code-instruct` | IBM's enterprise-ready code model — Apache 2.0, great for commercial use |
| 🏗️ IBM Granite 20B Code Instruct | `ibm-granite/granite-20b-code-instruct` | Larger Granite — better at multi-step refactoring and code explanation |

---

### 🧠 General Purpose & Reasoning

Well-rounded models that handle coding, explanation, Q&A, writing, and reasoning well. Good defaults if you want one model that does everything decently.

| Model | Repo ID | What it's for |
|---|---|---|
| 🌟 Llama 3.1 8B Instruct | `meta-llama/Meta-Llama-3.1-8B-Instruct` | Meta's workhorse — 128k context, solid all-rounder, very well supported |
| 🌟 Llama 3.1 70B Instruct | `meta-llama/Meta-Llama-3.1-70B-Instruct` | Full-fat Llama — best open general model at 70B, needs a big GPU |
| 🔥 Llama 3.3 70B Instruct | `meta-llama/Llama-3.3-70B-Instruct` | Updated 70B — better instruction following, sharper on reasoning tasks |
| 🦙 Llama 3.2 3B Instruct | `meta-llama/Llama-3.2-3B-Instruct` | Tiny but surprisingly capable — great for fast CPU inference |
| 🧪 Qwen2.5 7B Instruct | `Qwen/Qwen2.5-7B-Instruct` | Alibaba's best 7B — strong reasoning, math, and multilingual (29 languages) |
| 🧪 Qwen2.5 14B Instruct | `Qwen/Qwen2.5-14B-Instruct` | A big step up from 7B — often beats models twice its size on benchmarks |
| 🧪 Qwen2.5 72B Instruct | `Qwen/Qwen2.5-72B-Instruct` | Alibaba's flagship — top-tier open model, needs serious VRAM |
| 🧪 Qwen3 8B | `Qwen/Qwen3-8B` | Latest Qwen generation — hybrid thinking mode, very strong for its size |
| ⚡ Mistral 7B Instruct v0.3 | `mistralai/Mistral-7B-Instruct-v0.3` | Fast and capable — one of the best pure 7B models, great default |
| ⚡ Mistral Nemo 12B Instruct | `mistralai/Mistral-Nemo-Instruct-2407` | 12B sweet spot — longer context, better than 7B without needing GPU farm |
| 🔮 Gemma 2 9B IT | `google/gemma-2-9b-it` | Google's open model — clean, well-aligned, strong on explanation tasks |
| 🔮 Gemma 2 27B IT | `google/gemma-2-27b-it` | Larger Gemma — excellent at structured reasoning and technical writing |

---

### ⚡ Reasoning & Chain-of-Thought

These models are specifically trained to think step-by-step before answering. Slower token output, but dramatically better at hard problems — math, logic, debugging complex code.

| Model | Repo ID | What it's for |
|---|---|---|
| 🧮 DeepSeek-R1-Distill-Qwen-7B | `deepseek-ai/DeepSeek-R1-Distill-Qwen-7B` | R1 reasoning distilled into 7B — impressive chain-of-thought for the size |
| 🧮 DeepSeek-R1-Distill-Qwen-14B | `deepseek-ai/DeepSeek-R1-Distill-Qwen-14B` | Better R1 distill — stronger reasoning, still fits on a decent GPU |
| 🧮 DeepSeek-R1-Distill-Llama-8B | `deepseek-ai/DeepSeek-R1-Distill-Llama-8B` | R1 distilled on Llama 3 8B backbone — easy to run locally |
| 🔬 Phi-4-Mini-Reasoning | `microsoft/Phi-4-mini-reasoning` | Microsoft's 3.8B reasoning model — beats much larger models on math benchmarks |
| 🔬 Phi-4-Reasoning | `microsoft/Phi-4-reasoning` | Larger Phi-4 reasoning — strong on PhD-level math and science problems |
| 🧠 QwQ-32B | `Qwen/QwQ-32B` | Qwen's reasoning model — long internal monologue, great for hard coding problems |

---

### 🪶 Small & Fast (Low RAM / CPU)

Running on a laptop with 8GB RAM or no GPU? These are optimised for efficiency. Might not beat larger models on raw quality but they're actually usable on modest hardware.

| Model | Repo ID | What it's for |
|---|---|---|
| 🐦 Phi-3.5-Mini-Instruct | `microsoft/Phi-3.5-mini-instruct` | 3.8B from Microsoft — punches well above its weight, good for CPU |
| 🐦 Phi-3-Mini-4K-Instruct | `microsoft/Phi-3-mini-4k-instruct` | Older but very fast — good quality/speed tradeoff on CPU |
| 🧩 Qwen2.5 1.5B Instruct | `Qwen/Qwen2.5-1.5B-Instruct` | 1.5B model — shockingly capable for the size, runs on almost anything |
| 🧩 Qwen2.5 3B Instruct | `Qwen/Qwen2.5-3B-Instruct` | 3B sweet spot — better than 1.5B, still very fast on CPU |
| 🦙 Llama 3.2 1B Instruct | `meta-llama/Llama-3.2-1B-Instruct` | Meta's smallest — instant responses, good for testing or very low-end hardware |
| 💎 SmolLM2-1.7B-Instruct | `HuggingFaceTB/SmolLM2-1.7B-Instruct` | HuggingFace's own tiny model — surprisingly good at following instructions |
| 🔷 Granite 3B Code Instruct | `ibm-granite/granite-3b-code-instruct` | IBM's smallest code model — usable code completions with minimal RAM |

---

### 📚 Instruction Following & Writing

Models that are particularly good at following complex instructions, writing documentation, explanations, and structured output.

| Model | Repo ID | What it's for |
|---|---|---|
| 🌿 Zephyr 7B Beta | `HuggingFaceH4/zephyr-7b-beta` | HuggingFace's fine-tune of Mistral — very well-aligned, great for chat |
| 🌿 OpenHermes 2.5 Mistral 7B | `teknium/OpenHermes-2.5-Mistral-7B` | Community fine-tune — excellent instruction following, popular for good reason |
| 🌿 Neural-Chat 7B v3.3 | `Intel/neural-chat-7b-v3-3` | Intel's fine-tune — optimised for conversation, good for writing tasks |
| 🦅 Falcon 11B Instruct | `tiiuae/falcon-11b-instruct` | TII's model — good multilingual support and balanced output style |
| 🌊 Dolphin 2.9 Llama3 8B | `cognitivecomputations/dolphin-2.9-llama3-8b` | Uncensored Llama 3 fine-tune — very compliant with unusual or complex instructions |

---

### 🔬 Specialist & Domain-Specific

Trained on domain-specific corpora — useful if you work in a particular field and want a model that actually knows the terminology.

| Model | Repo ID | What it's for |
|---|---|---|
| 🧬 BioMistral 7B | `BioMistral/BioMistral-7B` | Biomedical focus — trained on PubMed, good for medical/research queries |
| ⚖️ Lawma 8B | `ricdomolm/lawma-8b` | Legal fine-tune of Llama 3 — understands legal language and document structure |
| 📊 FinGPT Llama 3.1 8B | `FinGPT/fingpt-mt_llama3.1-8b_lora` | Finance-focused — trained on financial news, earnings reports, market data |
| 🛡️ Granite Guardian 3.2 3B | `ibm-granite/granite-guardian-3.2-3b-a800m` | IBM's safety/moderation model — useful for evaluating outputs in a pipeline |

---

### 🌍 Multilingual

Built with strong support for non-English languages. If you're coding in a multilingual context or need to switch languages in chat.

| Model | Repo ID | What it's for |
|---|---|---|
| 🌐 Qwen2.5 7B Instruct | `Qwen/Qwen2.5-7B-Instruct` | Solid across 29 languages — one of the better multilingual small models |
| 🌐 Llama 3.1 8B Instruct | `meta-llama/Meta-Llama-3.1-8B-Instruct` | German, French, Italian, Portuguese, Hindi, Spanish, Thai + English |
| 🌐 Mistral Nemo 12B | `mistralai/Mistral-Nemo-Instruct-2407` | Built with multilingual use in mind — good European language support |
| 🌐 Aya Expanse 8B | `CohereForAI/aya-expanse-8b` | Cohere's multilingual model — trained to perform equally across 23 languages |
| 🌐 Aya Expanse 32B | `CohereForAI/aya-expanse-32b` | Larger Aya — stronger reasoning across all supported languages |

---

## ⌨️ Keyboard shortcuts

| Key | Action |
|---|---|
| `Enter` | Send message |
| `Shift + Enter` | New line in input |
| `Ctrl + L` | Clear the input box |
| `Ctrl + K` | Copy the last AI response |
| `■ Stop` | Kill generation mid-stream |

---

## 💻 Requirements

```
OS      →  Windows 10/11, Linux, macOS
Python  →  3.10+
RAM     →  8 GB min, 16 GB+ recommended
GPU     →  Optional — CUDA auto-detected, CPU works fine
Disk    →  ~15 GB per 7–8B model
```

---

## 🗺️ What's next

- [ ] GGUF / llama.cpp support for faster CPU inference
- [ ] Ollama backend as an alternative
- [ ] RAG — point it at a folder and chat with your codebase
- [ ] Custom theme editor (currently locked to dark green)
- [ ] Exportable system prompt profiles

Got an idea? Open an issue, I read them.

---

## 🤝 Contributing

Fork it, branch it, PR it. I'll take a look.

If something's broken or feels off, open an issue with your OS + Python version and I'll sort it out.

---

<div align="center">

<img src="https://capsule-render.vercel.app/api?type=waving&color=0:c77dff,33:4d96ff,66:6bcb77,100:ffd93d&height=120&section=footer&text=built+by+timdigga&fontSize=24&fontColor=ffffff&fontAlignY=65&animation=fadeIn" width="100%"/>

<br/>

[![GitHub followers](https://img.shields.io/github/followers/timdigga?label=Follow%20%40timdigga&style=social)](https://github.com/timdigga)
&nbsp;&nbsp;
[![Stars](https://img.shields.io/github/stars/timdigga?style=social)](https://github.com/timdigga)

**if this saves you time, a ⭐ goes a long way**

</div>
