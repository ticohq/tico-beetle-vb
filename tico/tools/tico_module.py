#!/usr/bin/env python3
"""Settings definition and translations for the tico module of Beetle VB.

Run after merging upstream. It builds tools/dump_core_options.c against the
core's own libretro_core_options.h, so tico/module/settings.json lists exactly
the options the libnx core reads (vb_* keys, values and defaults), laid
out in tabs, followed by the overlay's own display and controls options.
Labels are translation keys; the strings go into tico/lang/*.json, taken from
the LABELS and CHOICES tables below: the core translates none of tico's
languages. Choice labels stay English in settings.json; the overlay translates
them through settings_beetle_vb_value_* keys.

    python3 tico/tools/tico_module.py
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TICO = ROOT / "tico"
SETTINGS = TICO / "module/settings.json"
LANG_DIR = TICO / "lang"
LANGUAGES = ("en", "de", "es", "fr", "ja", "pt", "ru", "zh")
# tico-nx's own strings label the options it already knew; optional
TICO_NX = Path(os.environ.get("TICO_NX_DIR", ROOT.parents[1] / "tico-nx"))

# Core option -> label key. Options are named after their key without vb_.
LABEL_KEYS: dict[str, str] = {}

# Core options the frontend has no use for: tico presents one image, never
# both eyes of a VR view, and the frontend drives the right D-Pad from the
# right stick itself (Controls > Right stick as right D-Pad), sending the core
# no analog input to convert.
EXCLUDED = {"vb_vr", "vb_right_analog_to_digital"}

# (tab, [(section, [option keys])]). Every core option the dump lists must be
# placed or excluded; the overlay's own tabs are added around these.
LAYOUT = [
    ("settings_beetle_vb_tab_video", [
        ("settings_beetle_vb_section_display", ["vb_color_mode"]),
        ("settings_beetle_vb_section_3d", ["vb_3dmode", "vb_anaglyph_preset",
                                           "vb_sidebyside_separation"]),
    ]),
    ("settings_beetle_vb_tab_system", [
        ("settings_beetle_vb_section_system", ["vb_cpu_emulation"]),
        ("settings_beetle_vb_section_input", ["vb_opposite_directions"]),
    ]),
]

# Listed only while another option has a value, like the core's own menus.
DEPENDS_ON: dict[str, tuple[str, str]] = {
    "vb_anaglyph_preset": ("vb_3dmode", "anaglyph"),
    "vb_sidebyside_separation": ("vb_3dmode", "side-by-side"),
}

# English names for the core's lower-case values; numbers and the rest stay as
# the core spells them.
EN_CHOICES = {
    "anaglyph": "Anaglyph",
    "cyberscope": "CyberScope",
    "side-by-side": "Side by side",
    "vli": "Vertical line interlaced",
    "hli": "Horizontal line interlaced",
    "red & blue": "Red & blue",
    "red & cyan": "Red & cyan",
    "red & electric cyan": "Red & electric cyan",
    "green & magenta": "Green & magenta",
    "yellow & blue": "Yellow & blue",
    "black & red": "Black & red",
    "black & white": "Black & white",
    "black & blue": "Black & blue",
    "black & cyan": "Black & cyan",
    "black & electric cyan": "Black & electric cyan",
    "black & green": "Black & green",
    "black & magenta": "Black & magenta",
    "black & yellow": "Black & yellow",
    "accurate": "Accurate",
    "fast": "Fast",
}

# Switch buttons a Virtual Boy button (or the fast-forward hotkey) can sit on.
SWITCH_BUTTONS = [("A", "A"), ("B", "B"), ("X", "X"), ("Y", "Y"), ("L", "L"), ("R", "R"),
                  ("ZL", "ZL"), ("ZR", "ZR"), ("Plus", "Plus"), ("Minus", "Minus"),
                  ("StickL", "Left stick"), ("StickR", "Right stick"), ("Up", "Up"),
                  ("Down", "Down"), ("Left", "Left"), ("Right", "Right"), ("None", "Disabled")]

POSITIONS = [("hidden", "Hidden"), ("top_left", "Top left"), ("top_right", "Top right"),
             ("bottom_left", "Bottom left"), ("bottom_right", "Bottom right")]

# The overlay's own options: how the game is scaled, fast forward and the HUD.
# Shaders are picked in game (Settings > Shaders): tico cannot see the presets
# on the SD card. The Virtual Boy's 12:7 fills a 16:9 screen, so Original.
OVERLAY_TAB = ("settings_beetle_vb_tab_display", [
    ("settings_beetle_vb_section_screen", [
        {"key": "display_mode", "label": "settings_beetle_vb_display_mode", "type": "enum",
         "default": "Display", "choices": [("Integer", "Integer"), ("Display", "Display")]},
        {"key": "display_size", "label": "settings_beetle_vb_display_size", "type": "enum",
         "default": "Original", "choices": [("Stretch", "Stretch"), ("4:3", "4:3"),
                                            ("16:9", "16:9"), ("Original", "Original"),
                                            ("1x", "1x"), ("2x", "2x"), ("Auto", "Auto")]},
    ]),
    ("settings_beetle_vb_section_fast_forward", [
        {"key": "fast_forward_speed", "label": "settings_beetle_vb_fast_forward_speed", "type": "enum",
         "default": "200", "choices": [("150", "150%"), ("200", "200%"), ("300", "300%"),
                                        ("400", "400%"), ("unlimited", "Unlimited")]},
        {"key": "fast_forward_mode", "label": "settings_beetle_vb_fast_forward_mode", "type": "enum",
         "default": "hold", "choices": [("hold", "Hold"), ("toggle", "Toggle")]},
        {"key": "fast_forward_hotkey", "label": "settings_beetle_vb_fast_forward_hotkey",
         "type": "enum", "default": "ZR", "choices": SWITCH_BUTTONS},
    ]),
    ("settings_beetle_vb_section_hud", [
        {"key": "fps_counter_position", "label": "settings_beetle_vb_fps_counter", "type": "enum",
         "default": "hidden", "choices": POSITIONS},
        {"key": "rendered_ir_position", "label": "settings_beetle_vb_rendered_resolution",
         "type": "enum", "default": "hidden", "choices": POSITIONS},
    ]),
])

# The overlay's button mapping: Virtual Boy button -> Switch button. A, B, L
# and R sit on their namesakes and the left D-Pad on the D-Pad; the right
# D-Pad has no buttons by default, the right stick drives it
# (TicoMain.cpp's kButtonMappings).
CONTROLS_TAB = ("settings_beetle_vb_tab_controls", [
    ("settings_beetle_vb_section_button_mapping", [
        {"key": key, "label": "settings_beetle_vb_" + key, "type": "enum", "default": default,
         "choices": SWITCH_BUTTONS}
        for key, default in [
            ("map_a", "A"), ("map_b", "B"), ("map_l", "L"), ("map_r", "R"),
            ("map_start", "Plus"), ("map_select", "Minus"),
            ("map_left_up", "Up"), ("map_left_down", "Down"),
            ("map_left_left", "Left"), ("map_left_right", "Right"),
            ("map_right_up", "None"), ("map_right_down", "None"),
            ("map_right_left", "None"), ("map_right_right", "None"),
        ]
    ] + [
        {"key": "analog_dpad", "label": "settings_beetle_vb_analog_dpad", "type": "bool",
         "default": "enabled"},
        {"key": "right_stick_dpad", "label": "settings_beetle_vb_right_stick_dpad", "type": "bool",
         "default": "enabled"},
    ]),
])

# Labels the core does not define. key -> (en, de, es, fr, ja, pt, ru, zh)
LABELS = {
    "settings_beetle_vb_tab_video": ("Video", "Video", "Vídeo", "Vidéo", "ビデオ", "Vídeo", "Видео",
                                     "视频"),
    "settings_beetle_vb_section_display": ("Display", "Anzeige", "Pantalla", "Affichage", "表示",
                                           "Exibição", "Отображение", "显示"),
    "settings_beetle_vb_section_3d": ("3D", "3D", "3D", "3D", "3D", "3D", "3D", "3D"),
    "settings_beetle_vb_tab_system": ("System", "System", "Sistema", "Système", "システム",
                                      "Sistema", "Система", "系统"),
    "settings_beetle_vb_section_system": ("System", "System", "Sistema", "Système", "システム",
                                          "Sistema", "Система", "系统"),
    "settings_beetle_vb_section_input": ("Input", "Eingabe", "Entrada", "Entrée", "入力",
                                         "Entrada", "Ввод", "输入"),
    "settings_beetle_vb_color_mode": ("Palette", "Palette", "Paleta", "Palette", "パレット",
                                      "Paleta", "Палитра", "调色板"),
    "settings_beetle_vb_3dmode": ("3D mode", "3D-Modus", "Modo 3D", "Mode 3D", "3Dモード",
                                  "Modo 3D", "Режим 3D", "3D 模式"),
    "settings_beetle_vb_anaglyph_preset": ("Anaglyph colors", "Anaglyphen-Farben",
                                           "Colores anaglifo", "Couleurs anaglyphes",
                                           "アナグリフの色", "Cores do anáglifo",
                                           "Цвета анаглифа", "立体色彩"),
    "settings_beetle_vb_sidebyside_separation": ("Side-by-side separation",
                                                 "Abstand nebeneinander",
                                                 "Separación lado a lado",
                                                 "Écart côte à côte", "サイドバイサイドの間隔",
                                                 "Separação lado a lado",
                                                 "Разнос изображений", "左右分隔"),
    "settings_beetle_vb_cpu_emulation": ("CPU emulation", "CPU-Emulation", "Emulación de CPU",
                                         "Émulation du CPU", "CPUエミュレーション",
                                         "Emulação da CPU", "Эмуляция ЦП", "CPU 模拟"),
    "settings_beetle_vb_opposite_directions": ("Allow opposite directions",
                                               "Entgegengesetzte Richtungen erlauben",
                                               "Permitir direcciones opuestas",
                                               "Autoriser les directions opposées",
                                               "逆方向の同時入力を許可",
                                               "Permitir direções opostas",
                                               "Разрешить противоположные направления",
                                               "允许相反方向"),
    "settings_beetle_vb_tab_display": ("Display", "Anzeige", "Pantalla", "Affichage", "表示", "Tela",
                                       "Экран", "显示"),
    "settings_beetle_vb_section_screen": ("Screen", "Bild", "Imagen", "Image", "画面", "Imagem",
                                          "Изображение", "画面"),
    "settings_beetle_vb_section_hud": ("On-screen info", "Bildschirmanzeige",
                                       "Información en pantalla", "Affichage à l'écran", "画面表示",
                                       "Informações na tela", "Экранная информация", "屏幕信息"),
    "settings_beetle_vb_display_mode": ("Display Mode", "Anzeigemodus", "Modo de pantalla",
                                        "Mode d'affichage", "表示モード", "Modo de exibição",
                                        "Режим отображения", "显示模式"),
    "settings_beetle_vb_display_size": ("Size", "Größe", "Tamaño", "Taille", "サイズ", "Tamanho",
                                        "Размер", "尺寸"),
    "settings_beetle_vb_fps_counter": ("FPS counter", "FPS-Zähler", "Contador de FPS",
                                       "Compteur de FPS", "FPSカウンター", "Contador de FPS",
                                       "Счётчик FPS", "帧率计数器"),
    "settings_beetle_vb_rendered_resolution": ("Rendered resolution", "Gerenderte Auflösung",
                                               "Resolución renderizada", "Résolution de rendu",
                                               "描画解像度", "Resolução renderizada",
                                               "Разрешение рендеринга", "渲染分辨率"),
    "settings_beetle_vb_section_fast_forward": ("Fast Forward", "Vorspulen", "Avance rápido",
                                                "Avance rapide", "早送り", "Avanço rápido",
                                                "Перемотка", "快进"),
    "settings_beetle_vb_fast_forward_speed": ("Fast forward speed", "Vorspul-Geschwindigkeit",
                                              "Velocidad de avance rápido",
                                              "Vitesse d'avance rapide", "早送りの速度",
                                              "Velocidade do avanço rápido", "Скорость перемотки",
                                              "快进速度"),
    "settings_beetle_vb_fast_forward_mode": ("Fast forward mode", "Vorspul-Modus",
                                             "Modo de avance rápido", "Mode d'avance rapide",
                                             "早送りモード", "Modo do avanço rápido",
                                             "Режим перемотки", "快进模式"),
    "settings_beetle_vb_fast_forward_hotkey": ("Fast forward button", "Vorspul-Taste",
                                               "Botón de avance rápido", "Bouton d'avance rapide",
                                               "早送りボタン", "Botão do avanço rápido",
                                               "Кнопка перемотки", "快进按键"),
    "settings_beetle_vb_tab_controls": ("Controls", "Steuerung", "Controles", "Commandes", "操作",
                                        "Controles", "Управление", "控制"),
    "settings_beetle_vb_section_button_mapping": ("Button mapping", "Tastenbelegung",
                                                  "Asignación de botones",
                                                  "Attribution des boutons", "ボタン割り当て",
                                                  "Mapeamento de botões", "Назначение кнопок",
                                                  "按键映射"),
    "settings_beetle_vb_map_a": ("A", "A", "A", "A", "A", "A", "A", "A"),
    "settings_beetle_vb_map_b": ("B", "B", "B", "B", "B", "B", "B", "B"),
    "settings_beetle_vb_map_l": ("L", "L", "L", "L", "L", "L", "L", "L"),
    "settings_beetle_vb_map_r": ("R", "R", "R", "R", "R", "R", "R", "R"),
    "settings_beetle_vb_map_start": ("Start", "Start", "Start", "Start", "スタート", "Start",
                                     "Start", "开始"),
    "settings_beetle_vb_map_select": ("Select", "Select", "Select", "Select", "セレクト", "Select",
                                      "Select", "选择"),
    "settings_beetle_vb_map_left_up": ("Left D-Pad Up", "Linkes Steuerkreuz oben",
                                       "Cruceta izquierda arriba", "Croix gauche haut",
                                       "左十字キー上", "Direcional esquerdo para cima",
                                       "Левая крестовина вверх", "左方向键上"),
    "settings_beetle_vb_map_left_down": ("Left D-Pad Down", "Linkes Steuerkreuz unten",
                                         "Cruceta izquierda abajo", "Croix gauche bas",
                                         "左十字キー下", "Direcional esquerdo para baixo",
                                         "Левая крестовина вниз", "左方向键下"),
    "settings_beetle_vb_map_left_left": ("Left D-Pad Left", "Linkes Steuerkreuz links",
                                         "Cruceta izquierda a la izquierda",
                                         "Croix gauche gauche", "左十字キー左",
                                         "Direcional esquerdo para a esquerda",
                                         "Левая крестовина влево", "左方向键左"),
    "settings_beetle_vb_map_left_right": ("Left D-Pad Right", "Linkes Steuerkreuz rechts",
                                          "Cruceta izquierda a la derecha",
                                          "Croix gauche droite", "左十字キー右",
                                          "Direcional esquerdo para a direita",
                                          "Левая крестовина вправо", "左方向键右"),
    "settings_beetle_vb_map_right_up": ("Right D-Pad Up", "Rechtes Steuerkreuz oben",
                                        "Cruceta derecha arriba", "Croix droite haut",
                                        "右十字キー上", "Direcional direito para cima",
                                        "Правая крестовина вверх", "右方向键上"),
    "settings_beetle_vb_map_right_down": ("Right D-Pad Down", "Rechtes Steuerkreuz unten",
                                          "Cruceta derecha abajo", "Croix droite bas",
                                          "右十字キー下", "Direcional direito para baixo",
                                          "Правая крестовина вниз", "右方向键下"),
    "settings_beetle_vb_map_right_left": ("Right D-Pad Left", "Rechtes Steuerkreuz links",
                                          "Cruceta derecha a la izquierda",
                                          "Croix droite gauche", "右十字キー左",
                                          "Direcional direito para a esquerda",
                                          "Правая крестовина влево", "右方向键左"),
    "settings_beetle_vb_map_right_right": ("Right D-Pad Right", "Rechtes Steuerkreuz rechts",
                                           "Cruceta derecha a la derecha",
                                           "Croix droite droite", "右十字キー右",
                                           "Direcional direito para a direita",
                                           "Правая крестовина вправо", "右方向键右"),
    "settings_beetle_vb_analog_dpad": ("Left stick as left D-Pad",
                                       "Linker Stick als linkes Steuerkreuz",
                                       "Stick izquierdo como cruceta izquierda",
                                       "Stick gauche comme croix gauche",
                                       "左スティックを左十字キーとして使う",
                                       "Analógico esquerdo como direcional esquerdo",
                                       "Левый стик как левая крестовина",
                                       "左摇杆作为左方向键"),
    "settings_beetle_vb_right_stick_dpad": ("Right stick as right D-Pad",
                                            "Rechter Stick als rechtes Steuerkreuz",
                                            "Stick derecho como cruceta derecha",
                                            "Stick droit comme croix droite",
                                            "右スティックを右十字キーとして使う",
                                            "Analógico direito como direcional direito",
                                            "Правый стик как правая крестовина",
                                            "右摇杆作为右方向键"),
}

# Choice labels the core does not translate. English -> (de, es, fr, ja, pt, ru, zh)
CHOICES = {
    "Anaglyph": ("Anaglyphen", "Anaglifo", "Anaglyphe", "アナグリフ", "Anáglifo", "Анаглиф",
                 "红蓝立体"),
    "CyberScope": ("CyberScope", "CyberScope", "CyberScope", "CyberScope", "CyberScope",
                   "CyberScope", "CyberScope"),
    "Side by side": ("Nebeneinander", "Lado a lado", "Côte à côte", "サイドバイサイド",
                     "Lado a lado", "Бок о бок", "左右并排"),
    "Vertical line interlaced": ("Zeilenweise vertikal", "Entrelazado vertical",
                                 "Entrelacé vertical", "縦ライン交互", "Entrelaçado vertical",
                                 "Чересстрочно по вертикали", "垂直交错"),
    "Horizontal line interlaced": ("Zeilenweise horizontal", "Entrelazado horizontal",
                                   "Entrelacé horizontal", "横ライン交互",
                                   "Entrelaçado horizontal", "Чересстрочно по горизонтали",
                                   "水平交错"),
    "Red & blue": ("Rot & Blau", "Rojo y azul", "Rouge et bleu", "赤と青", "Vermelho e azul",
                   "Красный и синий", "红与蓝"),
    "Red & cyan": ("Rot & Cyan", "Rojo y cian", "Rouge et cyan", "赤とシアン", "Vermelho e ciano",
                   "Красный и голубой", "红与青"),
    "Red & electric cyan": ("Rot & Elektrocyan", "Rojo y cian eléctrico", "Rouge et cyan électrique",
                            "赤とエレクトリックシアン", "Vermelho e ciano elétrico",
                            "Красный и электрик", "红与电光青"),
    "Green & magenta": ("Grün & Magenta", "Verde y magenta", "Vert et magenta", "緑とマゼンタ",
                        "Verde e magenta", "Зелёный и пурпурный", "绿与品红"),
    "Yellow & blue": ("Gelb & Blau", "Amarillo y azul", "Jaune et bleu", "黄と青",
                      "Amarelo e azul", "Жёлтый и синий", "黄与蓝"),
    "Black & red": ("Schwarz & Rot", "Negro y rojo", "Noir et rouge", "黒と赤", "Preto e vermelho",
                    "Чёрный и красный", "黑与红"),
    "Black & white": ("Schwarz & Weiß", "Negro y blanco", "Noir et blanc", "黒と白",
                      "Preto e branco", "Чёрный и белый", "黑与白"),
    "Black & blue": ("Schwarz & Blau", "Negro y azul", "Noir et bleu", "黒と青", "Preto e azul",
                     "Чёрный и синий", "黑与蓝"),
    "Black & cyan": ("Schwarz & Cyan", "Negro y cian", "Noir et cyan", "黒とシアン", "Preto e ciano",
                     "Чёрный и голубой", "黑与青"),
    "Black & electric cyan": ("Schwarz & Elektrocyan", "Negro y cian eléctrico",
                              "Noir et cyan électrique", "黒とエレクトリックシアン",
                              "Preto e ciano elétrico", "Чёрный и электрик", "黑与电光青"),
    "Black & green": ("Schwarz & Grün", "Negro y verde", "Noir et vert", "黒と緑", "Preto e verde",
                      "Чёрный и зелёный", "黑与绿"),
    "Black & magenta": ("Schwarz & Magenta", "Negro y magenta", "Noir et magenta", "黒とマゼンタ",
                        "Preto e magenta", "Чёрный и пурпурный", "黑与品红"),
    "Black & yellow": ("Schwarz & Gelb", "Negro y amarillo", "Noir et jaune", "黒と黄",
                       "Preto e amarelo", "Чёрный и жёлтый", "黑与黄"),
    "Accurate": ("Genau", "Precisa", "Précise", "正確", "Precisa", "Точная", "精确"),
    "Fast": ("Schnell", "Rápida", "Rapide", "高速", "Rápida", "Быстрая", "快速"),
    "Disabled": ("Deaktiviert", "Desactivado", "Désactivé", "無効", "Desativado", "Выключено",
                 "禁用"),
    "Enabled": ("Aktiviert", "Activado", "Activé", "有効", "Ativado", "Включено", "启用"),
    "Integer": ("Ganzzahlig", "Entero", "Entier", "整数倍", "Inteiro", "Целочисленный", "整数"),
    "Display": ("Anzeige", "Pantalla", "Écran", "画面", "Tela", "Экран", "屏幕"),
    "Stretch": ("Strecken", "Estirar", "Étirer", "引き伸ばし", "Esticar", "Растянуть", "拉伸"),
    "Original": ("Original", "Original", "Original", "オリジナル", "Original", "Оригинал", "原始"),
    "Auto": ("Auto", "Auto", "Auto", "自動", "Auto", "Авто", "自动"),
    "Unlimited": ("Unbegrenzt", "Ilimitado", "Illimité", "無制限", "Ilimitado", "Без ограничений",
                  "无限制"),
    "Hold": ("Halten", "Mantener", "Maintenir", "長押し", "Segurar", "Удерживать", "按住"),
    "Toggle": ("Umschalten", "Alternar", "Basculer", "切り替え", "Alternar", "Переключать", "切换"),
    "Right stick": ("Rechter Stick", "Stick derecho", "Stick droit", "右スティック", "Analógico direito",
                    "Правый стик", "右摇杆"),
    "Left stick": ("Linker Stick", "Stick izquierdo", "Stick gauche", "左スティック", "Analógico esquerdo",
                   "Левый стик", "左摇杆"),
    "Plus": ("Plus", "Más", "Plus", "プラス", "Mais", "Плюс", "加号"),
    "Minus": ("Minus", "Menos", "Moins", "マイナス", "Menos", "Минус", "减号"),
    "Up": ("Oben", "Arriba", "Haut", "上", "Cima", "Вверх", "上"),
    "Down": ("Unten", "Abajo", "Bas", "下", "Baixo", "Вниз", "下"),
    "Left": ("Links", "Izquierda", "Gauche", "左", "Esquerda", "Влево", "左"),
    "Right": ("Rechts", "Derecha", "Droite", "右", "Direita", "Вправо", "右"),
    "Hidden": ("Ausgeblendet", "Oculto", "Masqué", "非表示", "Oculto", "Скрыто", "隐藏"),
    "Top left": ("Oben links", "Arriba a la izquierda", "En haut à gauche", "左上",
                 "Superior esquerdo", "Сверху слева", "左上"),
    "Top right": ("Oben rechts", "Arriba a la derecha", "En haut à droite", "右上",
                  "Superior direito", "Сверху справа", "右上"),
    "Bottom left": ("Unten links", "Abajo a la izquierda", "En bas à gauche", "左下",
                    "Inferior esquerdo", "Снизу слева", "左下"),
    "Bottom right": ("Unten rechts", "Abajo a la derecha", "En bas à droite", "右下",
                     "Inferior direito", "Снизу справа", "右下"),
}

RESTART_SUFFIX = re.compile(r"\s*\(([Rr]equires restart|Restart Required|Restart|Reload Core|[^)]*[Nn]eustart[^)]*|[^)]*[Rr]einici[^)]*|"
                            r"[^)]*[Rr]edémarr[^)]*|[^)]*再起動[^)]*|[^)]*перезапуск[^)]*|"
                            r"[^)]*重启[^)]*|[^)]*[Rr]einicializa[^)]*)\)")


def value_key(label: str) -> str:
    """tico_config.cpp's ValueKey: settings_beetle_vb_value_ + label as a slug."""
    return "settings_beetle_vb_value_" + "_".join(re.findall(r"[a-z0-9]+", label.lower()))


def clean_label(text: str) -> str:
    return RESTART_SUFFIX.sub("", text).lstrip("> ").strip()


def english_choice(value: str, label: str) -> str:
    # the core leaves its values unlabelled, most in lower case
    if label != value:
        return label
    if value in ("disabled", "enabled"):
        return label.capitalize()
    return EN_CHOICES.get(value, label)


def dump_options() -> dict:
    with tempfile.TemporaryDirectory() as tmp:
        exe = Path(tmp) / "dump_core_options"
        # the libnx build has no VR (HAVE_VR), so the VR-only options are out
        subprocess.run(["cc", "-std=gnu11", "-w",
                        "-I", str(ROOT),
                        "-I", str(ROOT / "libretro-common/include"),
                        "-o", str(exe), str(Path(__file__).with_name("dump_core_options.c"))],
                       check=True)
        return json.loads(subprocess.run([str(exe)], check=True, capture_output=True,
                                         text=True).stdout)


def label_key(key: str) -> str:
    return LABEL_KEYS.get(key, "settings_beetle_vb_" + key.removeprefix("vb_"))


def build_settings(dump: dict) -> dict:
    core = {o["key"]: o for o in dump["en"]}
    placed = {key for _, sections in LAYOUT for _, keys in sections for key in keys}
    missing = sorted(set(core) - placed - EXCLUDED)
    if missing:
        raise SystemExit(f"core options not placed in LAYOUT: {missing}")

    tabs = []
    for tab, sections in LAYOUT:
        out_sections = []
        for title, keys in sections:
            options = []
            for key in keys:
                source = core[key]
                values = [v for v, _ in source["values"]]
                option = {"key": key, "label": label_key(key)}
                if sorted(values) == ["disabled", "enabled"]:
                    option.update(type="bool", default=source["default"])
                else:
                    option.update(type="enum", default=source["default"], choices=[
                        {"label": english_choice(v, l), "value": v} for v, l in source["values"]])
                if RESTART_SUFFIX.search(source["desc"]):
                    option["restart"] = True
                if key in DEPENDS_ON:
                    on, value = DEPENDS_ON[key]
                    option["depends_on"] = {"key": on, "value": value}
                options.append(option)
            out_sections.append({"title": title, "options": options})
        tabs.append({"name": tab, "sections": out_sections})

    def overlay_tab(definition):
        tab, sections = definition
        return {"name": tab, "sections": [
            {"title": title, "options": [
                {**o, "choices": [{"label": l, "value": v} for v, l in o["choices"]]}
                if "choices" in o else dict(o)
                for o in options]}
            for title, options in sections]}

    tabs.insert(1, overlay_tab(OVERLAY_TAB))
    tabs.append(overlay_tab(CONTROLS_TAB))

    return {
        "core_id": "beetle_vb",
        "display_name": "Beetle VB",
        "config_file": "beetle_vb.jsonc",
        "slugs": ["vb"],
        "bool_true_value": "enabled",
        "bool_false_value": "disabled",
        "tabs": tabs,
    }


def tico_owned(key: str) -> bool:
    """Labels tico itself defines, whose wording tico keeps."""
    return key in LABEL_KEYS.values() or key.startswith(("settings_beetle_vb_tab_",
                                                          "settings_beetle_vb_section_"))


def build_strings(dump: dict, settings: dict,
                  existing: dict[str, dict[str, str]]) -> dict[str, dict[str, str]]:
    strings: dict[str, dict[str, str]] = {lang: {} for lang in LANGUAGES}
    english = {o["key"]: o for o in dump["en"]}
    for lang in LANGUAGES:
        out = strings[lang]
        index = LANGUAGES.index(lang)
        for option in dump[lang]:
            if option["key"] in EXCLUDED or option["key"] not in english:
                continue
            key, en = option["key"], english[option["key"]]
            out[label_key(key)] = clean_label(option["desc"])
            # by value: a translation may list the choices differently
            en_labels = dict(en["values"])
            for value, label in option["values"]:
                if label is None or value not in en_labels:
                    continue
                en_text = english_choice(value, en_labels[value])
                if label != en_labels[value]:
                    out[value_key(en_text)] = label
        for key, texts in LABELS.items():
            out[key] = texts[index]
        if lang != "en":
            for choice, translations in CHOICES.items():
                out[value_key(choice)] = translations[index - 1]
        if lang == "en":
            for key in list(out):
                if key.startswith("settings_beetle_vb_value_"):
                    del out[key]
    # tico's own labels keep tico's wording: from tico-nx when it is checked
    # out, otherwise as the language files already have them
    for lang in LANGUAGES:
        path = TICO_NX / "assets/lang" / f"{lang}.json"
        source = json.loads(path.read_text()) if path.exists() else existing[lang]
        for key, value in source.items():
            if tico_owned(key):
                strings[lang][key] = value
    used = set()

    def walk(node):
        if isinstance(node, dict):
            for field in ("label", "name", "title"):
                if isinstance(node.get(field), str) and node[field].startswith("settings_"):
                    used.add(node[field])
            for child in node.values():
                walk(child)
        elif isinstance(node, list):
            for child in node:
                walk(child)

    walk(settings)
    unlabelled = sorted(used - set(strings["en"]))
    if unlabelled:
        raise SystemExit(f"labels without English text: {unlabelled}")
    return strings


def main() -> None:
    dump = dump_options()
    settings = build_settings(dump)
    SETTINGS.write_text(json.dumps(settings, indent=2, ensure_ascii=False) + "\n")
    current_files = {lang: json.loads((LANG_DIR / f"{lang}.json").read_text())
                     if (LANG_DIR / f"{lang}.json").exists() else {} for lang in LANGUAGES}
    for lang, strings in build_strings(dump, settings, current_files).items():
        path = LANG_DIR / f"{lang}.json"
        current = {k: v for k, v in current_files[lang].items()
                   if not k.startswith("settings_beetle_vb_")}
        current.update(dict(sorted(strings.items())))
        path.write_text(json.dumps(current, indent=4, ensure_ascii=False) + "\n")
    print(f"wrote {SETTINGS.relative_to(ROOT)} and {len(LANGUAGES)} language files")


if __name__ == "__main__":
    main()
