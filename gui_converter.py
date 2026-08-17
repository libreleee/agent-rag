"""
한글 (HWP / HWPX) ➔ PDF / Word (.docx) 폴더 일괄 변환 GUI 프로그램
Windows Native Desktop Application
"""
import os
import sys
import threading
from pathlib import Path
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from src.utils.hwp_to_pdf import convert_hwp_to_pdf
from src.utils.hwp_to_docx import convert_hwp_to_docx


class HwpDocConverterGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("한글(HWP/HWPX) ➔ PDF & Word(.docx) 폴더 일괄 변환기")
        self.root.geometry("820x680")
        self.root.minsize(720, 560)

        self.bg_color = "#1e1e2e"
        self.card_bg = "#252538"
        self.fg_color = "#cdd6f4"
        self.accent_color = "#89b4fa"
        self.btn_accent = "#a6e3a1"
        
        self.root.configure(bg=self.bg_color)
        self.is_converting = False
        
        self.create_widgets()

    def create_widgets(self):
        # Header Container
        header_frame = tk.Frame(self.root, bg=self.bg_color, pady=15)
        header_frame.pack(fill="x", padx=20)
        
        title_label = tk.Label(
            header_frame, 
            text="⚡ 한글(HWP / HWPX) ➔ PDF & Word(.docx) 일괄 변환기", 
            font=("Malgun Gothic", 16, "bold"),
            bg=self.bg_color,
            fg="#f5e0dc"
        )
        title_label.pack(anchor="w")
        
        sub_label = tk.Label(
            header_frame,
            text="폴더를 선택하면 내부의 모든 한글 문서를 PDF 또는 Word(.docx)로 자동 일괄 변환하여 저장합니다.",
            font=("Malgun Gothic", 9),
            bg=self.bg_color,
            fg="#a6adc8"
        )
        sub_label.pack(anchor="w", pady=(3, 0))

        # Main Card Frame
        main_card = tk.Frame(self.root, bg=self.card_bg, padx=20, pady=18, relief="flat")
        main_card.pack(fill="x", padx=20, pady=5)

        # 1. Input Folder Selection
        tk.Label(
            main_card, 
            text="📂 변환할 한글 파일들이 있는 원본 폴더 (입력):", 
            font=("Malgun Gothic", 10, "bold"),
            bg=self.card_bg, 
            fg=self.fg_color
        ).grid(row=0, column=0, sticky="w", pady=(0, 4))

        self.input_dir_var = tk.StringVar()
        input_entry = tk.Entry(
            main_card, 
            textvariable=self.input_dir_var, 
            font=("Malgun Gothic", 10),
            bg="#181825", 
            fg="#ffffff", 
            insertbackground="#ffffff",
            relief="flat",
            bd=5
        )
        input_entry.grid(row=1, column=0, sticky="ew", padx=(0, 10), pady=(0, 14))

        btn_input_browse = tk.Button(
            main_card, 
            text="📁 폴더 선택...", 
            font=("Malgun Gothic", 9, "bold"),
            bg="#313244", 
            fg="#89b4fa",
            activebackground="#45475a",
            activeforeground="#b4befe",
            relief="flat",
            padx=14, 
            pady=4,
            cursor="hand2",
            command=self.browse_input_dir
        )
        btn_input_browse.grid(row=1, column=1, pady=(0, 14))

        # 2. Output Folder Selection
        tk.Label(
            main_card, 
            text="📁 변환 결과 파일을 저장할 대상 폴더 (출력):", 
            font=("Malgun Gothic", 10, "bold"),
            bg=self.card_bg, 
            fg=self.fg_color
        ).grid(row=2, column=0, sticky="w", pady=(0, 4))

        self.output_dir_var = tk.StringVar()
        output_entry = tk.Entry(
            main_card, 
            textvariable=self.output_dir_var, 
            font=("Malgun Gothic", 10),
            bg="#181825", 
            fg="#ffffff", 
            insertbackground="#ffffff",
            relief="flat",
            bd=5
        )
        output_entry.grid(row=3, column=0, sticky="ew", padx=(0, 10), pady=(0, 12))

        btn_output_browse = tk.Button(
            main_card, 
            text="📁 폴더 선택...", 
            font=("Malgun Gothic", 9, "bold"),
            bg="#313244", 
            fg="#89b4fa",
            activebackground="#45475a",
            activeforeground="#b4befe",
            relief="flat",
            padx=14, 
            pady=4,
            cursor="hand2",
            command=self.browse_output_dir
        )
        btn_output_browse.grid(row=3, column=1, pady=(0, 12))

        # 3. Target Format Selection Radio Buttons
        format_frame = tk.Frame(main_card, bg=self.card_bg)
        format_frame.grid(row=4, column=0, columnspan=2, sticky="w", pady=(4, 0))

        tk.Label(
            format_frame,
            text="🎯 변환할 대상 포맷:",
            font=("Malgun Gothic", 10, "bold"),
            bg=self.card_bg,
            fg="#f9e2af"
        ).pack(side="left", padx=(0, 15))

        self.format_var = tk.StringVar(value="pdf")
        
        rb_pdf = tk.Radiobutton(
            format_frame,
            text="📄 PDF 문서 (*.pdf)",
            variable=self.format_var,
            value="pdf",
            font=("Malgun Gothic", 10, "bold"),
            bg=self.card_bg,
            fg="#a6e3a1",
            selectcolor="#181825",
            activebackground=self.card_bg,
            activeforeground="#a6e3a1",
            cursor="hand2"
        )
        rb_pdf.pack(side="left", padx=(0, 20))

        rb_docx = tk.Radiobutton(
            format_frame,
            text="📝 Word 문서 (*.docx)",
            variable=self.format_var,
            value="docx",
            font=("Malgun Gothic", 10, "bold"),
            bg=self.card_bg,
            fg="#89b4fa",
            selectcolor="#181825",
            activebackground=self.card_bg,
            activeforeground="#89b4fa",
            cursor="hand2"
        )
        rb_docx.pack(side="left")

        main_card.columnconfigure(0, weight=1)

        # 4. Action Buttons
        action_frame = tk.Frame(self.root, bg=self.bg_color, pady=10)
        action_frame.pack(fill="x", padx=20)

        self.btn_convert = tk.Button(
            action_frame,
            text="🚀 전체 일괄 변환 시작",
            font=("Malgun Gothic", 12, "bold"),
            bg=self.btn_accent,
            fg="#11111b",
            activebackground="#94e2d5",
            activeforeground="#11111b",
            relief="flat",
            pady=10,
            cursor="hand2",
            command=self.start_conversion_thread
        )
        self.btn_convert.pack(side="left", fill="x", expand=True, padx=(0, 10))

        self.btn_open_folder = tk.Button(
            action_frame,
            text="📂 결과 폴더 열기",
            font=("Malgun Gothic", 10, "bold"),
            bg="#313244",
            fg="#cdd6f4",
            activebackground="#45475a",
            activeforeground="#ffffff",
            relief="flat",
            pady=10,
            padx=16,
            cursor="hand2",
            command=self.open_output_folder
        )
        self.btn_open_folder.pack(side="right")

        # 5. Progress & Status
        progress_frame = tk.Frame(self.root, bg=self.bg_color)
        progress_frame.pack(fill="x", padx=20, pady=(2, 6))

        self.status_var = tk.StringVar(value="준비 완료: 원본 폴더와 저장 포맷을 선택 후 [일괄 변환 시작]을 눌러주세요.")
        self.status_label = tk.Label(
            progress_frame,
            textvariable=self.status_var,
            font=("Malgun Gothic", 9),
            bg=self.bg_color,
            fg="#a6adc8",
            anchor="w"
        )
        self.status_label.pack(fill="x", pady=(0, 4))

        self.progress = ttk.Progressbar(progress_frame, orient="horizontal", mode="determinate")
        self.progress.pack(fill="x")

        # 6. Log Box Frame
        log_frame = tk.Frame(self.root, bg=self.bg_color)
        log_frame.pack(fill="both", expand=True, padx=20, pady=(10, 15))

        tk.Label(
            log_frame,
            text="📋 실시간 변환 로그:",
            font=("Malgun Gothic", 9, "bold"),
            bg=self.bg_color,
            fg="#a6adc8"
        ).pack(anchor="w", pady=(0, 4))

        self.log_text = tk.Text(
            log_frame,
            bg="#11111b",
            fg="#cdd6f4",
            insertbackground="#ffffff",
            font=("Consolas", 9),
            relief="flat",
            bd=5
        )
        self.log_text.pack(fill="both", expand=True, side="left")

        scrollbar = tk.Scrollbar(log_frame, command=self.log_text.yview)
        scrollbar.pack(side="right", fill="y")
        self.log_text.config(yscrollcommand=scrollbar.set)

    def browse_input_dir(self):
        dir_selected = filedialog.askdirectory(title="한글 파일(.hwp, .hwpx)이 있는 폴더 선택")
        if dir_selected:
            self.input_dir_var.set(dir_selected)
            if not self.output_dir_var.get():
                target_fmt = self.format_var.get()
                sub = "docx_output" if target_fmt == "docx" else "pdf_output"
                default_out = str(Path(dir_selected) / sub)
                self.output_dir_var.set(default_out)
            self.log(f"📥 원본 폴더 지정: {dir_selected}")

    def browse_output_dir(self):
        dir_selected = filedialog.askdirectory(title="결과 파일을 저장할 폴더 선택")
        if dir_selected:
            self.output_dir_var.set(dir_selected)
            self.log(f"📁 저장 폴더 지정: {dir_selected}")

    def log(self, message):
        self.log_text.insert("end", message + "\n")
        self.log_text.see("end")

    def open_output_folder(self):
        out_dir = self.output_dir_var.get().strip()
        if out_dir and os.path.exists(out_dir):
            os.startfile(out_dir)
        else:
            messagebox.showwarning("알림", "출력 폴더가 아직 생성되지 않았거나 존재하지 않습니다.")

    def start_conversion_thread(self):
        if self.is_converting:
            return

        input_dir = self.input_dir_var.get().strip()
        output_dir = self.output_dir_var.get().strip()
        target_fmt = self.format_var.get()

        if not input_dir or not os.path.isdir(input_dir):
            messagebox.showerror("오류", "변환할 원본 폴더를 올바르게 선택해주세요.")
            return

        if not output_dir:
            sub = "docx_output" if target_fmt == "docx" else "pdf_output"
            output_dir = str(Path(input_dir) / sub)
            self.output_dir_var.set(output_dir)

        t = threading.Thread(target=self.run_batch_conversion, args=(input_dir, output_dir, target_fmt), daemon=True)
        t.start()

    def run_batch_conversion(self, input_dir, output_dir, target_fmt):
        self.is_converting = True
        self.btn_convert.config(state="disabled", text=f"⏳ {target_fmt.upper()} 일괄 변환 진행 중...")
        self.progress["value"] = 0

        input_path = Path(input_dir)
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        supported_exts = {".hwp", ".hwpx", ".doc", ".docx"}
        files = [f for f in input_path.iterdir() if f.is_file() and f.suffix.lower() in supported_exts]

        total = len(files)
        if total == 0:
            self.status_var.set("선택한 폴더에 변환 대상 파일(.hwp, .hwpx)이 없습니다.")
            self.log("❌ 변환 대상 파일(.hwp, .hwpx, .doc, .docx)이 없습니다.")
            self.is_converting = False
            self.btn_convert.config(state="normal", text="🚀 전체 일괄 변환 시작")
            return

        self.log(f"🔍 총 {total}개의 한글 문서를 발견했습니다. (목표: {target_fmt.upper()})")
        self.log(f"📁 저장 위치: {output_path}")
        self.log("-" * 65)

        success_count = 0
        fail_count = 0

        for idx, file in enumerate(files, 1):
            self.status_var.set(f"변환 중 ({idx}/{total}): {file.name} ➔ {target_fmt.upper()}")
            self.log(f"[{idx}/{total}] 변환 시작: {file.name} ...")
            
            try:
                if target_fmt == "docx":
                    out_doc = convert_hwp_to_docx(str(file), output_dir=str(output_path))
                else:
                    out_doc = convert_hwp_to_pdf(str(file), output_dir=str(output_path))
                self.log(f"  └─ ✅ 완료: {out_doc.name}")
                success_count += 1
            except Exception as e:
                self.log(f"  └─ ❌ 실패: {str(e)}")
                fail_count += 1

            self.progress["value"] = (idx / total) * 100
            self.root.update_idletasks()

        self.log("-" * 65)
        self.log(f"🎉 변환 완료! 성공: {success_count}건, 실패: {fail_count}건")
        self.status_var.set(f"작업 완료! ({target_fmt.upper()} 성공: {success_count}개, 실패: {fail_count}개)")
        
        self.is_converting = False
        self.btn_convert.config(state="normal", text="🚀 전체 일괄 변환 시작")

        messagebox.showinfo(
            "변환 완료", 
            f"총 {total}개 파일 중 {success_count}개 {target_fmt.upper()} 변환 완료되었습니다!\n\n저장 폴더: {output_path}"
        )


def main():
    root = tk.Tk()
    app = HwpDocConverterGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
