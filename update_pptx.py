import os
import re
import glob
from datetime import date, timedelta
from pptx import Presentation
from pptx.util import Emu, Pt
from pptx.dml.color import RGBColor
from pptx.oxml.ns import qn

VIEWS_DIR = r'C:\Users\shc72\iCloudDrive\01. 수원온누리교회\※ views'
PPTX_DIR  = r'C:\Users\shc72\iCloudDrive\01. 수원온누리교회\02. 수요성령집회'


def find_numbered_images(folder):
    result = []
    for f in os.listdir(folder):
        name, ext = os.path.splitext(f)
        if name.isdigit() and ext.lower() in ('.jpg', '.jpeg', '.png', '.gif', '.bmp'):
            result.append((int(name), os.path.join(folder, f)))
    result.sort()
    return [path for _, path in result]


def get_next_wednesday():
    today = date.today()
    days = (2 - today.weekday()) % 7
    return (today + timedelta(days=days)).strftime('%Y%m%d')


def find_pptx(folder):
    files = [f for f in glob.glob(os.path.join(folder, '*.pptx'))
             if not os.path.basename(f).startswith('~$')]
    if not files:
        raise FileNotFoundError(f'pptx 파일 없음: {folder}')
    return files[0]


def clear_slide(slide):
    sp_tree = slide.shapes._spTree
    for shape in list(slide.shapes):
        sp_tree.remove(shape._element)


def ensure_two_slides(prs):
    blank = prs.slide_layouts[6]
    while len(prs.slides) < 2:
        prs.slides.add_slide(blank)
    while len(prs.slides) > 2:
        idx = len(prs.slides) - 1
        rId = prs.slides._sldIdLst[idx].get(qn('r:id'))
        prs.slides._sldIdLst.remove(prs.slides._sldIdLst[idx])
        del prs.part.related_parts[rId]


def add_textbox(slide, left, top, width, height, text, font_size=None, bold=None):
    txBox = slide.shapes.add_textbox(left, top, width, height)
    txBox.line.color.rgb = RGBColor(0, 0, 0)
    txBox.line.width = Pt(1.5)
    tf = txBox.text_frame
    run = tf.paragraphs[0].add_run()
    run.text = text
    if font_size:
        run.font.size = font_size
    if bold is not None:
        run.font.bold = bold


def update_pptx():
    images = find_numbered_images(VIEWS_DIR)
    print(f'이미지 {len(images)}개 발견: {[os.path.basename(p) for p in images]}')

    pptx_path = find_pptx(PPTX_DIR)
    print(f'pptx: {os.path.basename(pptx_path)}')

    wednesday = get_next_wednesday()
    print(f'수요일 날짜: {wednesday}')

    total = len(images)
    default_mid = (total + 1) // 2
    try:
        n_str = input(f'\n슬라이드 1에 이미지 몇 개? (전체 {total}개, 기본 {default_mid}): ').strip()
        mid = int(n_str) if n_str else default_mid
        mid = max(1, min(mid, total - 1))
    except ValueError:
        mid = default_mid
    print(f'슬라이드 1: {mid}개 / 슬라이드 2: {total - mid}개\n')
    groups = [images[:mid], images[mid:]]

    # 기존 pptx 열기
    prs = Presentation(pptx_path)
    slide_w = prs.slide_width
    slide_h = prs.slide_height

    # 원본 텍스트박스 정보 저장
    orig_tb = None
    for shape in prs.slides[0].shapes:
        if shape.has_text_frame:
            orig_tb = {'left': shape.left, 'top': shape.top,
                       'width': shape.width, 'height': shape.height,
                       'text': shape.text_frame.text,
                       'font_size': shape.text_frame.paragraphs[0].runs[0].font.size if shape.text_frame.paragraphs[0].runs else None,
                       'bold': shape.text_frame.paragraphs[0].runs[0].font.bold if shape.text_frame.paragraphs[0].runs else None}
            break

    title_text = re.sub(r'\d{8}', wednesday, orig_tb['text']) if orig_tb else f'{wednesday} 수요성령집회 콘티'

    # 슬라이드 2장으로 맞추기
    ensure_two_slides(prs)

    # 각 슬라이드 내용 초기화 후 재구성
    for slide_idx, group in enumerate(groups):
        slide = prs.slides[slide_idx]
        clear_slide(slide)

        top_offset = Emu(0)
        if slide_idx == 0 and orig_tb:
            add_textbox(slide, orig_tb['left'], orig_tb['top'],
                        orig_tb['width'], orig_tb['height'],
                        title_text, orig_tb['font_size'], orig_tb['bold'])
            top_offset = orig_tb['top'] + orig_tb['height']

        n = len(group)
        img_w = slide_w // n
        img_h = slide_h - top_offset

        for i, img_path in enumerate(group):
            slide.shapes.add_picture(img_path, img_w * i, top_offset, img_w, img_h)
            print(f'  슬라이드 {slide_idx + 1} [{i + 1}/{n}]: {os.path.basename(img_path)}')

    try:
        prs.save(pptx_path)
        print(f'\n완료! 저장: {pptx_path}')
    except PermissionError:
        print(f'\n오류: 파일이 열려있습니다. PowerPoint를 닫고 다시 실행하세요.')


if __name__ == '__main__':
    update_pptx()
