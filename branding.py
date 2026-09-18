"""Identidad institucional configurable y cabecera común para informes PDF."""
import json
import shutil
from pathlib import Path
from uuid import uuid4
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from PIL import Image as PILImage, ImageTk

BASE = Path(__file__).resolve().parent
DEFAULT_LOGO = 'assets/uca_logo.png'


def logo_path(config):
    path = Path(config.get('logo_path') or DEFAULT_LOGO)
    if not path.is_absolute(): path = BASE/path
    if not path.is_file(): raise ValueError('No se encuentra el logotipo. Selecciónelo en Configuración > Identidad / PDF.')
    with PILImage.open(path) as image: image.verify()
    return path


def pdf_page_branding(config):
    from reportlab.lib.utils import ImageReader
    from reportlab.lib.units import mm
    reader=ImageReader(str(logo_path(config)))
    width,height=reader.getSize(); scale=min(48*mm/width,18*mm/height)
    def paint(canvas,doc):
        canvas.saveState(); page_width,page_height=doc.pagesize
        canvas.drawImage(reader,doc.leftMargin,page_height-25*mm,width=width*scale,height=height*scale,mask='auto')
        canvas.setFillColorRGB(.09,.22,.32); canvas.setFont('Helvetica',10)
        canvas.drawRightString(page_width-doc.rightMargin,page_height-15*mm,'Laboratorio de ensayo - Prensa Marshall')
        canvas.setStrokeColorRGB(.8,.85,.9); canvas.line(doc.leftMargin,page_height-29*mm,page_width-doc.rightMargin,page_height-29*mm)
        canvas.setFont('Helvetica',8); canvas.setFillColorRGB(.35,.4,.45)
        canvas.drawString(doc.leftMargin,8*mm,'Universidad de Cádiz | Adquisición de fuerza y deformación')
        canvas.drawRightString(page_width-doc.rightMargin,8*mm,f'Página {doc.page}')
        canvas.restoreState()
    return paint


class BrandingUI:
    def build_logo_header(self,header):
        self.logo_label=ttk.Label(header,text='Espacio para logotipo UCA',width=23)
        self.logo_label.pack(side='left',padx=(0,14))
        self.refresh_logo()

    def refresh_logo(self):
        try:
            with PILImage.open(logo_path(self.cfg)) as source:
                preview=source.copy(); preview.thumbnail((155,58))
            self.logo_photo=ImageTk.PhotoImage(preview,master=self)
            self.logo_label.configure(image=self.logo_photo,text='',width='')
        except (OSError,ValueError):
            self.logo_label.configure(image='',text='Espacio para logotipo UCA',width=23)

    def build_branding_config(self,notebook):
        tab=ttk.Frame(notebook,padding=18); notebook.add(tab,text='Identidad / PDF')
        ttk.Label(tab,text='Universidad de Cádiz',font=('Segoe UI',18,'bold')).pack(anchor='w')
        ttk.Label(tab,text='El logotipo aparece en la aplicación y en la cabecera de todas las páginas de los informes PDF.\nSe conserva su proporción original. Puede sustituirlo por la versión institucional de su laboratorio.',wraplength=850).pack(anchor='w',pady=12)
        self.logo_status=tk.StringVar(value=self.cfg.get('logo_path',DEFAULT_LOGO))
        ttk.Label(tab,textvariable=self.logo_status,wraplength=850).pack(anchor='w',pady=8)
        ttk.Button(tab,text='Seleccionar logotipo PNG / JPG',command=self.choose_logo).pack(anchor='w',pady=8)
        ttk.Button(tab,text='Restaurar logotipo oficial UCA',command=lambda:self.save_logo(DEFAULT_LOGO)).pack(anchor='w')
        ttk.Label(tab,text='Fuente del logotipo incluido: Gabinete de Comunicación y Marketing de la UCA.\nVersión 1, horizontal, color. No se ha redibujado ni alterado.',wraplength=850).pack(anchor='w',pady=18)

    def save_logo(self,path):
        try:
            candidate=dict(self.cfg,logo_path=str(path)); logo_path(candidate)
            tmp=self.cfg_path.with_suffix('.tmp'); tmp.write_text(json.dumps(candidate,indent=2,ensure_ascii=False),encoding='utf-8'); tmp.replace(self.cfg_path)
            self.cfg=candidate; self.refresh_logo(); self.logo_status.set(str(path)); self.status.set('Logotipo guardado para la aplicación y los PDF')
        except (OSError,ValueError) as exc: messagebox.showerror('Logotipo',str(exc))

    def choose_logo(self):
        path=filedialog.askopenfilename(filetypes=[('Imagen PNG / JPG','*.png *.jpg *.jpeg')])
        if not path:return
        try:
            logo_path({'logo_path':path})
            directory=self.cfg_path.parent/'assets'; directory.mkdir(exist_ok=True)
            target=directory/('logo_'+uuid4().hex+Path(path).suffix.lower())
            shutil.copyfile(path,target); self.save_logo(target)
        except (OSError,ValueError) as exc: messagebox.showerror('Logotipo',str(exc))
