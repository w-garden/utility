import glob
import os
import sys
import configparser
import tkinter as tk
from tkinter import filedialog, messagebox
from datetime import date, timedelta

from pptx import Presentation
from pptx.util import Emu, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_AUTO_SIZE
from pptx.oxml.ns import qn

CONFIG_FILENAME = 'config.ini'

BG       = '#0f1428'
CARD_BG  = '#1a2040'
ACCENT   = '#5080e0'
FG       = '#ffffff'
FG_DIM   = '#8898cc'
BORDER   = '#2a3560'
SUCCESS  = '#2a6040'
ERROR    = '#602a40'
FONT     = '맑은 고딕'


def _base_dir() -> str:
    return os.path.dirname(sys.executable if getattr(sys, 'frozen', False) else os.path.abspath(__file__))


def _config_path() -> str:
    return os.path.join(_base_dir(), CONFIG_FILENAME)


def load_config() -> tuple[str, str]:
    cfg = configparser.ConfigParser()
    cfg.read(_config_path(), encoding='utf-8')
    views = cfg.get('paths', 'views_dir', fallback='').strip()
    pptx  = cfg.get('paths', 'pptx_dir',  fallback='').strip()
    return views, pptx


def save_config(views: str, pptx: str) -> None:
    cfg = configparser.ConfigParser()
    cfg['paths'] = {'views_dir': views, 'pptx_dir': pptx}
    with open(_config_path(), 'w', encoding='utf-8') as f:
        cfg.write(f)


def find_numbered_images(folder: str) -> list[str]:
    import re
    if not os.path.isdir(folder):
        return []
    files = [
        f for f in os.listdir(folder)
        if os.path.splitext(f)[1].lower() in ('.jpg', '.jpeg', '.png', '.gif', '.bmp')
    ]
    files.sort(key=lambda f: [int(t) if t.isdigit() else t.lower() for t in re.split(r'(\d+)', f)])
    return [os.path.join(folder, f) for f in files]


def next_wednesday() -> str:
    today = date.today()
    days = (2 - today.weekday()) % 7 or 7
    return (today + timedelta(days=days)).strftime('%Y%m%d')


def find_or_create_pptx(folder: str, title: str) -> tuple[str, str | None]:
    """(저장할 경로, 기존 파일 경로 or None) 반환. 항상 {title}.pptx로 저장."""
    os.makedirs(folder, exist_ok=True)
    save_path = os.path.join(folder, f'{title}.pptx')
    files = [f for f in glob.glob(os.path.join(folder, '*.pptx'))
             if not os.path.basename(f).startswith('~$')]
    existing = files[0] if files else None
    if not existing:
        prs = Presentation()
        prs.slides.add_slide(prs.slide_layouts[6])
        prs.save(save_path)
    return save_path, existing


def run_update(views_dir: str, pptx_dir: str, title: str, split: int) -> str:
    images = find_numbered_images(views_dir)
    if not images:
        raise ValueError(f'이미지가 없습니다.\n폴더: {views_dir}')

    total = len(images)
    split = max(1, min(split, total - 1)) if total > 1 else total
    groups = [images[:split], images[split:]] if total > 1 else [images, []]

    save_path, existing = find_or_create_pptx(pptx_dir, title)
    prs = Presentation(existing or save_path)
    slide_w = prs.slide_width
    slide_h = prs.slide_height

    # 슬라이드 수 맞추기
    blank = prs.slide_layouts[6]
    needed = len([g for g in groups if g])
    while len(prs.slides) < needed:
        prs.slides.add_slide(blank)
    while len(prs.slides) > needed:
        idx = len(prs.slides) - 1
        rId = prs.slides._sldIdLst[idx].get(qn('r:id'))
        prs.slides._sldIdLst.remove(prs.slides._sldIdLst[idx])
        del prs.part.related_parts[rId]

    slide_num = 0
    for group in groups:
        if not group:
            continue
        slide = prs.slides[slide_num]
        sp_tree = slide.shapes._spTree
        for shape in list(slide.shapes):
            sp_tree.remove(shape._element)

        top_offset = Emu(0)
        if slide_num == 0:
            tb_h = Pt(32)
            txBox = slide.shapes.add_textbox(Emu(0), Emu(0), slide_w, tb_h)
            tf = txBox.text_frame
            tf.auto_size = MSO_AUTO_SIZE.SHAPE_TO_FIT_TEXT
            tf.margin_top = Emu(0)
            tf.margin_bottom = Emu(0)
            tf.margin_left = Emu(0)
            tf.margin_right = Emu(0)
            run = tf.paragraphs[0].add_run()
            tf.paragraphs[0].alignment = PP_ALIGN.LEFT
            run.text = title
            run.font.size = Pt(22)
            run.font.bold = False
            run.font.name = '맑은 고딕'
            top_offset = tb_h + Pt(2)

        n = len(group)
        img_w = slide_w // n
        img_h = slide_h - top_offset
        for i, img_path in enumerate(group):
            slide.shapes.add_picture(img_path, img_w * i, top_offset, img_w, img_h)

        slide_num += 1

    prs.save(save_path)
    return f'({total}장 → {needed}슬라이드) {os.path.basename(save_path)}', save_path


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title('콘티 악보 생성')
        self.resizable(False, False)
        self.configure(bg=BG)

        views, pptx = load_config()
        self.views_var = tk.StringVar(value=views)
        self.pptx_var  = tk.StringVar(value=pptx)

        wed = next_wednesday()
        self.title_var = tk.StringVar(value=f'{wed} 수요성령집회 콘티')
        self.split_var = tk.IntVar(value=1)
        self._last_pptx = None

        self._build_ui()
        self._center()

    def _label(self, parent, text):
        return tk.Label(parent, text=text, bg=CARD_BG, fg=FG_DIM, font=(FONT, 9))

    def _entry(self, parent, var, width=38):
        return tk.Entry(parent, textvariable=var, width=width,
                        bg=BG, fg=FG, insertbackground=FG,
                        relief='flat', highlightthickness=1,
                        highlightbackground=BORDER, highlightcolor=ACCENT,
                        font=(FONT, 10))

    def _btn(self, parent, text, cmd, small=False):
        return tk.Button(parent, text=text, command=cmd,
                         bg=ACCENT, fg=FG, activebackground='#3a60c0',
                         activeforeground=FG, relief='flat', cursor='hand2',
                         font=(FONT, 9 if small else 11, 'bold'),
                         padx=8 if small else 16, pady=4 if small else 10)

    def _folder_row(self, parent, label, var, row):
        self._label(parent, label).grid(row=row, column=0, columnspan=2, sticky='w', pady=(12, 2))
        e = self._entry(parent, var, width=34)
        e.grid(row=row+1, column=0, sticky='ew', padx=(0, 6))
        self._btn(parent, '변경', lambda: self._pick(var), small=True).grid(row=row+1, column=1)

    def _build_ui(self):
        card = tk.Frame(self, bg=CARD_BG, padx=28, pady=24)
        card.pack(padx=16, pady=16)

        tk.Label(card, text='콘티 악보 생성', bg=CARD_BG, fg=FG,
                 font=(FONT, 14, 'bold')).grid(row=0, column=0, columnspan=2, sticky='w')
        tk.Label(card, text='이미지 → PPT', bg=CARD_BG, fg=FG_DIM,
                 font=(FONT, 9)).grid(row=1, column=0, columnspan=2, sticky='w', pady=(2, 8))

        self._folder_row(card, '이미지 폴더 (views)', self.views_var, 2)
        self._folder_row(card, 'PPT 저장 폴더', self.pptx_var, 4)

        self._label(card, '제목').grid(row=6, column=0, columnspan=2, sticky='w', pady=(12, 2))
        self._entry(card, self.title_var).grid(row=7, column=0, columnspan=2, sticky='ew')

        self._label(card, '슬라이드 한 장에 넣을 이미지 수').grid(row=8, column=0, columnspan=2, sticky='w', pady=(12, 2))
        self._entry(card, self.split_var, width=8).grid(row=9, column=0, sticky='w')

        self._btn(card, '실행', self._run).grid(row=10, column=0, columnspan=2, sticky='ew', pady=(20, 0))

        self.status = tk.Label(card, text='', bg=CARD_BG, fg=FG_DIM,
                               font=(FONT, 9), wraplength=360, justify='left')
        self.status.grid(row=11, column=0, columnspan=2, sticky='w', pady=(10, 0))

        btn_frame = tk.Frame(card, bg=CARD_BG)
        btn_frame.grid(row=12, column=0, columnspan=2, sticky='ew', pady=(8, 0))
        btn_frame.columnconfigure(0, weight=1)
        btn_frame.columnconfigure(1, weight=1)

        self.open_file_btn = self._btn(btn_frame, '파일 열기', self._open_file_direct)
        self.open_file_btn.grid(row=0, column=0, sticky='ew', padx=(0, 4))
        self.open_file_btn.grid_remove()

        self.open_folder_btn = self._btn(btn_frame, '폴더 열기', self._open_folder)
        self.open_folder_btn.grid(row=0, column=1, sticky='ew', padx=(4, 0))
        self.open_folder_btn.grid_remove()

        card.columnconfigure(0, weight=1)

    def _pick(self, var):
        path = filedialog.askdirectory(initialdir=var.get() or os.path.expanduser('~'))
        if path:
            var.set(path)
            save_config(self.views_var.get(), self.pptx_var.get())

    def _open_folder(self):
        if self._last_pptx and os.path.exists(self._last_pptx):
            os.startfile(os.path.dirname(self._last_pptx))

    def _open_file_direct(self):
        if self._last_pptx and os.path.exists(self._last_pptx):
            os.startfile(self._last_pptx)

    def _run(self):
        views = self.views_var.get().strip()
        pptx  = self.pptx_var.get().strip()
        title = self.title_var.get().strip()
        split = self.split_var.get()

        if not views or not pptx:
            messagebox.showwarning('경고', '폴더를 선택해주세요.')
            return
        if not title:
            messagebox.showwarning('경고', '제목을 입력해주세요.')
            return

        save_config(views, pptx)
        self.open_folder_btn.grid_remove()
        self.open_file_btn.grid_remove()
        self.status.config(text='실행 중...', fg=FG_DIM)
        self.update()

        try:
            msg, pptx_path = run_update(views, pptx, title, split)
            self._last_pptx = pptx_path
            self.status.config(text=f'완료! {msg}', fg='#80e0a0')
            self.open_folder_btn.grid()
            self.open_file_btn.grid()
        except PermissionError:
            self.status.config(text='❌ PPTX 파일이 열려있습니다. PowerPoint를 닫고 다시 실행하세요.', fg='#e08080')
        except Exception as e:
            self.status.config(text=f'❌ {e}', fg='#e08080')

    def _center(self):
        self.update_idletasks()
        w, h = self.winfo_width(), self.winfo_height()
        x = (self.winfo_screenwidth()  - w) // 2
        y = (self.winfo_screenheight() - h) // 2
        self.geometry(f'+{x}+{y}')


if __name__ == '__main__':
    App().mainloop()
