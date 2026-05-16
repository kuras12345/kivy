"""
Aplikacja dla instruktora nauki jazdy.
- do 24 kursantów
- każdy musi wyjeździć 30 h
- egzamin 40 min
Dane zapisywane lokalnie w pliku JSON (app.user_data_dir).
"""
import json
import os
from datetime import datetime, timedelta

from kivy.app import App
from kivy.lang import Builder
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.uix.popup import Popup
from kivy.uix.spinner import Spinner
from kivy.properties import StringProperty
from kivy.core.window import Window
from kivy.utils import platform
from kivy.clock import Clock

# Tylko na iOS/Android: przy aktywnym polu tekstowym przesuwaj zawartość
# tak, by pole było nad klawiaturą ekranową. Na desktopie pozostawiamy
# domyślne zachowanie, żeby nic nie skakało.
if platform in ('ios', 'android'):
    Window.softinput_mode = 'below_target'

REQUIRED_HOURS = 30
EXAM_DURATION = 40  # minuty
MAX_STUDENTS = 24
HOUR_CHOICES = [f'{h:02d}:00' for h in range(5, 24)]  # 05:00 ... 23:00
SCHOOL_START_DATE = '2025-09-01'  # najwcześniejsza data dostępna w spinnerach


def parse_hhmm(text):
    """Zwraca obiekt time z 'HH:MM' / 'H:MM' lub None."""
    text = text.strip().replace('.', ':')
    try:
        return datetime.strptime(text, '%H:%M').time()
    except ValueError:
        return None


def hours_between(start, end):
    """Liczba godzin (float) między dwoma obiektami time. Obsługuje północ."""
    today = datetime(2000, 1, 1)
    a = datetime.combine(today, start)
    b = datetime.combine(today, end)
    if b <= a:
        b += timedelta(days=1)
    return (b - a).total_seconds() / 3600.0


def date_choices(since=None, back=30, ahead=14):
    """Lista dat 'YYYY-MM-DD' do wyboru w Spinnerze.

    Kolejność: dzisiaj → kolejne dni do przodu → ostatnie dni wstecz.
    Jeżeli podane jest `since` ('YYYY-MM-DD'), wstecz idziemy aż do tej
    daty (parametr `back` jest wtedy ignorowany).
    """
    today = datetime.now().date()
    if since:
        start = datetime.strptime(since, '%Y-%m-%d').date()
        back = max(0, (today - start).days)
    items = [today.strftime('%Y-%m-%d')]
    items += [(today + timedelta(days=i)).strftime('%Y-%m-%d')
              for i in range(1, ahead + 1)]
    items += [(today - timedelta(days=i)).strftime('%Y-%m-%d')
              for i in range(1, back + 1)]
    return items


def show_info(text, title='Info'):
    """Prosty popup informacyjny (używany w wielu miejscach)."""
    content = BoxLayout(orientation='vertical', spacing=8, padding=10)
    lbl = Label(text=text, halign='center', valign='middle', font_size='17sp')
    lbl.bind(size=lambda w, *a: setattr(w, 'text_size', w.size))
    content.add_widget(lbl)
    ok = Button(text='OK', size_hint_y=None, height=56, font_size='18sp')
    content.add_widget(ok)
    p = Popup(title=title, content=content,
              size_hint=(0.85, 0.4), title_size='18sp')
    ok.bind(on_release=p.dismiss)
    p.open()

KV = '''
ScreenManager:
    StudentListScreen:
    StudentDetailScreen:

<StudentListScreen>:
    name: 'list'
    BoxLayout:
        orientation: 'vertical'
        padding: 10
        spacing: 8

        Label:
            text: 'Nauka jazdy — kursanci'
            font_size: '26sp'
            bold: True
            size_hint_y: None
            height: '54dp'

        Label:
            text: root.stats_text
            size_hint_y: None
            height: '128dp'
            font_size: '15sp'
            halign: 'center'
            valign: 'middle'
            text_size: self.width, None
            color: 0.95, 0.95, 0.97, 1
            markup: True

        ScrollView:
            GridLayout:
                id: students_container
                cols: 1
                spacing: 6
                size_hint_y: None
                height: self.minimum_height
                padding: [0, 4, 0, 4]

        Button:
            text: '+ Dodaj kursanta'
            size_hint_y: None
            height: '60dp'
            font_size: '20sp'
            bold: True
            background_normal: ''
            background_color: 0.2, 0.7, 0.3, 1
            on_release: root.add_student_popup()

<StudentDetailScreen>:
    name: 'student_detail'
    BoxLayout:
        orientation: 'vertical'
        padding: 10
        spacing: 8

        BoxLayout:
            size_hint_y: None
            height: '54dp'
            spacing: 6
            Button:
                text: '< Wstecz'
                size_hint_x: 0.35
                font_size: '17sp'
                background_normal: ''
                background_color: 0.5, 0.5, 0.55, 1
                on_release: root.manager.current = 'list'
            Label:
                text: root.title_text
                font_size: '21sp'
                bold: True

        Label:
            text: root.hours_text
            size_hint_y: None
            height: '36dp'
            font_size: '18sp'

        Label:
            text: root.exam_text
            size_hint_y: None
            height: '32dp'
            font_size: '17sp'

        Label:
            text: 'Historia jazd:'
            size_hint_y: None
            height: '32dp'
            font_size: '17sp'
            bold: True
            halign: 'left'
            text_size: self.size

        ScrollView:
            GridLayout:
                id: sessions_container
                cols: 1
                spacing: 4
                size_hint_y: None
                height: self.minimum_height

        BoxLayout:
            size_hint_y: None
            height: '60dp'
            spacing: 6
            Button:
                id: add_session_btn
                text: '+ Jazda'
                font_size: '19sp'
                bold: True
                background_normal: ''
                background_color: 0.2, 0.7, 0.3, 1
                background_disabled_normal: ''
                disabled_color: 1, 1, 1, 1
                on_release: root.add_session_popup()
            Button:
                id: exam_btn
                text: 'Egzamin'
                font_size: '19sp'
                bold: True
                background_normal: ''
                background_color: 0.9, 0.5, 0.1, 1
                background_disabled_normal: ''
                disabled_color: 1, 1, 1, 1
                on_release: root.exam_popup()
'''


# -------- Dane --------

class DataStore:
    def __init__(self, path):
        self.path = path
        self.data = self._load()

    def _load(self):
        if os.path.exists(self.path):
            try:
                with open(self.path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception:
                pass
        return {'students': [], 'next_id': 1}

    def save(self):
        try:
            with open(self.path, 'w', encoding='utf-8') as f:
                json.dump(self.data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print('Błąd zapisu:', e)

    def add_student(self, first, last):
        s = {
            'id': self.data.get('next_id', 1),
            'first_name': first.strip(),
            'last_name': last.strip(),
            'sessions': [],
            'exam': None,
        }
        self.data['students'].append(s)
        self.data['next_id'] = s['id'] + 1
        self.save()
        return s

    def remove_student(self, sid):
        self.data['students'] = [s for s in self.data['students'] if s['id'] != sid]
        self.save()

    def get(self, sid):
        for s in self.data['students']:
            if s['id'] == sid:
                return s
        return None

    def add_session(self, sid, date, start, end):
        """Dodaje jazdę. start/end w formacie 'HH:MM'. Hours liczone automatycznie."""
        s = self.get(sid)
        if not s:
            return
        st = parse_hhmm(start)
        en = parse_hhmm(end)
        hours = hours_between(st, en) if (st and en) else 0.0
        s['sessions'].append({
            'date': date,
            'start': start,
            'end': end,
            'hours': float(hours),
        })
        s['sessions'].sort(
            key=lambda x: (x['date'], x.get('start', '')), reverse=True
        )
        self.save()

    def remove_session(self, sid, idx):
        s = self.get(sid)
        if s and 0 <= idx < len(s['sessions']):
            s['sessions'].pop(idx)
            self.save()

    def total(self, sid):
        s = self.get(sid)
        return sum(x['hours'] for x in s['sessions']) if s else 0

    def total_all_hours(self):
        """Suma godzin wszystkich jazd wszystkich kursantów."""
        return sum(
            x['hours']
            for s in self.data['students']
            for x in s.get('sessions', [])
        )

    def total_remaining_hours(self):
        """Suma niedoborów godzin do REQUIRED_HOURS (po wszystkich kursantach)."""
        rem = 0.0
        for s in self.data['students']:
            t = sum(x['hours'] for x in s.get('sessions', []))
            rem += max(0.0, REQUIRED_HOURS - t)
        return rem

    def exam_counts(self):
        """Zwraca (zdane, niezdane, nie_podchodzili)."""
        passed = failed = none = 0
        for s in self.data['students']:
            ex = s.get('exam')
            if ex is None:
                none += 1
            elif ex.get('passed'):
                passed += 1
            else:
                failed += 1
        return passed, failed, none

    def finished_count(self):
        """Liczba kursantów, którzy wyjeździli min. wymagane h I zdali egzamin."""
        n = 0
        for s in self.data['students']:
            total = sum(x['hours'] for x in s.get('sessions', []))
            ex = s.get('exam')
            if total >= REQUIRED_HOURS and ex and ex.get('passed'):
                n += 1
        return n

    def set_exam(self, sid, passed, date):
        s = self.get(sid)
        if s:
            s['exam'] = {'passed': passed, 'date': date, 'duration': EXAM_DURATION}
            self.save()


# -------- Ekrany --------

class StudentListScreen(Screen):
    stats_text = StringProperty('')

    def on_pre_enter(self):
        # KV-children mogą jeszcze nie być zaaplikowane przy pierwszym wejściu,
        # więc odraczamy odświeżenie do następnej klatki.
        Clock.schedule_once(lambda dt: self.refresh(), 0)

    def refresh(self, *_):
        app = App.get_running_app()
        cont = self.ids.get('students_container')
        if cont is None:
            Clock.schedule_once(lambda dt: self.refresh(), 0)
            return
        cont.clear_widgets()

        students = app.store.data['students']
        finished = app.store.finished_count()
        total_hours = app.store.total_all_hours()
        remaining_hours = app.store.total_remaining_hours()
        passed, failed, none_exam = app.store.exam_counts()
        exams_taken = passed + failed

        self.stats_text = (
            f"[b]Kursantów:[/b] {len(students)}/{MAX_STUDENTS}   "
            f"[b]Ukończonych:[/b] {finished}\n"
            f"[b]Łączny czas jazd:[/b] {round(total_hours)} h   "
            f"[b]Pozostało:[/b] {round(remaining_hours)} h\n"
            f"[b]Egzaminów łącznie:[/b] {exams_taken}   "
            f"[b]Pozostało:[/b] {none_exam}"
        )

        if not students:
            empty = Label(
                text='Brak kursantów.\nDotknij "+ Dodaj kursanta".',
                size_hint_y=None, height=140, halign='center', valign='middle',
                font_size='17sp',
            )
            empty.bind(size=lambda w, *a: setattr(w, 'text_size', w.size))
            cont.add_widget(empty)
            return

        for s in students:
            total = app.store.total(s['id'])
            exam = s.get('exam')
            if exam and exam.get('passed'):
                ex = '✓ zdany'
            elif exam:
                ex = '✗ niezdany'
            else:
                ex = '—'
            done = total >= REQUIRED_HOURS

            row = BoxLayout(orientation='horizontal',
                            size_hint_y=None, height=110, spacing=4)

            bg = (0.85, 0.97, 0.85, 1) if done else (0.95, 0.95, 0.97, 1)
            info = Button(
                text=f"[b][size=20]{s['first_name']} {s['last_name']}[/size][/b]\n"
                     f"[size=16]{total:.1f} / {REQUIRED_HOURS} h  •  Egz: {ex}[/size]",
                markup=True,
                halign='left', valign='middle',
                size_hint_x=0.82,
                background_normal='',
                background_color=bg,
                color=(0.1, 0.1, 0.1, 1),
            )
            info.bind(size=lambda b, *a: setattr(b, 'text_size', (b.width - 16, None)))
            info.bind(on_release=lambda b, sid=s['id']: self.open_student(sid))

            del_btn = Button(
                text='X', size_hint_x=0.18, font_size='22sp', bold=True,
                background_normal='', background_color=(0.8, 0.25, 0.25, 1),
            )
            del_btn.bind(on_release=lambda b, sid=s['id'],
                         name=f"{s['first_name']} {s['last_name']}":
                         self.confirm_delete(sid, name))

            row.add_widget(info)
            row.add_widget(del_btn)
            cont.add_widget(row)

    def open_student(self, sid):
        App.get_running_app().current_student_id = sid
        self.manager.current = 'student_detail'

    def add_student_popup(self):
        app = App.get_running_app()
        if len(app.store.data['students']) >= MAX_STUDENTS:
            self._info_popup(f'Osiągnięto limit {MAX_STUDENTS} kursantów.')
            return

        content = BoxLayout(orientation='vertical', spacing=8, padding=10)
        fn = TextInput(hint_text='Imię', multiline=False,
                       size_hint_y=None, height=56, font_size='18sp')
        ln = TextInput(hint_text='Nazwisko', multiline=False,
                       size_hint_y=None, height=56, font_size='18sp')
        msg = Label(text='', size_hint_y=None, height=30,
                    font_size='15sp', color=(0.8, 0.2, 0.2, 1))

        btns = BoxLayout(size_hint_y=None, height=60, spacing=6)
        cancel = Button(text='Anuluj', font_size='18sp')
        save = Button(text='Zapisz', font_size='18sp', bold=True,
                      background_normal='', background_color=(0.2, 0.7, 0.3, 1))
        btns.add_widget(cancel)
        btns.add_widget(save)

        content.add_widget(Label(text='Imię:', size_hint_y=None, height=28,
                                 font_size='16sp', halign='left'))
        content.add_widget(fn)
        content.add_widget(Label(text='Nazwisko:', size_hint_y=None, height=28,
                                 font_size='16sp', halign='left'))
        content.add_widget(ln)
        content.add_widget(msg)
        content.add_widget(btns)

        popup = Popup(title='Nowy kursant', content=content,
                      size_hint=(0.94, 0.7), title_size='18sp')

        def do_save(*_):
            if not fn.text.strip() or not ln.text.strip():
                msg.text = 'Podaj imię i nazwisko.'
                return
            app.store.add_student(fn.text, ln.text)
            popup.dismiss()
            self.refresh()

        save.bind(on_release=do_save)
        cancel.bind(on_release=popup.dismiss)
        popup.open()

    def confirm_delete(self, sid, name):
        content = BoxLayout(orientation='vertical', spacing=10, padding=10)
        lbl = Label(text=f'Usunąć kursanta:\n{name}?\nTo skasuje też historię jazd.',
                    halign='center', valign='middle', font_size='17sp')
        lbl.bind(size=lambda w, *a: setattr(w, 'text_size', w.size))
        content.add_widget(lbl)
        btns = BoxLayout(size_hint_y=None, height=60, spacing=6)
        no = Button(text='Anuluj', font_size='18sp')
        yes = Button(text='Usuń', font_size='18sp', bold=True,
                     background_normal='', background_color=(0.8, 0.25, 0.25, 1))
        btns.add_widget(no)
        btns.add_widget(yes)
        content.add_widget(btns)
        popup = Popup(title='Potwierdź', content=content,
                      size_hint=(0.88, 0.5), title_size='18sp')
        yes.bind(on_release=lambda *_:
                 (App.get_running_app().store.remove_student(sid),
                  popup.dismiss(), self.refresh()))
        no.bind(on_release=popup.dismiss)
        popup.open()

    def _info_popup(self, text):
        content = BoxLayout(orientation='vertical', spacing=8, padding=10)
        lbl = Label(text=text, halign='center', valign='middle',
                    font_size='17sp')
        lbl.bind(size=lambda w, *a: setattr(w, 'text_size', w.size))
        content.add_widget(lbl)
        ok = Button(text='OK', size_hint_y=None, height=56, font_size='18sp')
        content.add_widget(ok)
        p = Popup(title='Info', content=content,
                  size_hint=(0.85, 0.4), title_size='18sp')
        ok.bind(on_release=p.dismiss)
        p.open()


class StudentDetailScreen(Screen):
    title_text = StringProperty('')
    hours_text = StringProperty('')
    exam_text = StringProperty('')

    def on_pre_enter(self):
        Clock.schedule_once(lambda dt: self.refresh(), 0)

    def refresh(self, *_):
        app = App.get_running_app()
        sid = app.current_student_id
        s = app.store.get(sid)
        if not s:
            self.manager.current = 'list'
            return

        self.title_text = f"{s['first_name']} {s['last_name']}"
        total = app.store.total(sid)
        remaining = max(0, REQUIRED_HOURS - total)
        self.hours_text = (f"Wyjeżdżone: {round(total)} / {REQUIRED_HOURS} h"
                           f"   (pozostało {round(remaining)} h)")

        add_btn = self.ids.get('add_session_btn')
        if add_btn is not None:
            if total >= REQUIRED_HOURS:
                add_btn.disabled = True
                add_btn.text = 'Komplet 30 h \u2713'
                add_btn.background_color = (0.4, 0.5, 0.4, 1)
            else:
                add_btn.disabled = False
                add_btn.text = '+ Jazda'
                add_btn.background_color = (0.2, 0.7, 0.3, 1)

        exam = s.get('exam')
        if exam:
            status = 'ZDANY' if exam.get('passed') else 'NIEZDANY ✗'
            self.exam_text = f"Egzamin ({EXAM_DURATION} min): {status}  •  {exam.get('date', '')}"
        else:
            self.exam_text = f"Egzamin ({EXAM_DURATION} min): nie podszedł"

        exam_btn = self.ids.get('exam_btn')
        if exam_btn is not None:
            if exam:
                exam_btn.disabled = True
                exam_btn.text = ('Egzamin zdany' if exam.get('passed')
                                 else 'Egzamin niezdany \u2717')
                exam_btn.background_color = (0.5, 0.5, 0.5, 1)
            else:
                exam_btn.disabled = False
                exam_btn.text = 'Egzamin'
                exam_btn.background_color = (0.9, 0.5, 0.1, 1)

        cont = self.ids.get('sessions_container')
        if cont is None:
            Clock.schedule_once(lambda dt: self.refresh(), 0)
            return
        cont.clear_widgets()

        if not s['sessions']:
            cont.add_widget(Label(
                text='Brak wpisanych jazd.',
                size_hint_y=None, height=70,
                font_size='17sp',
                color=(0.5, 0.5, 0.5, 1)
            ))
            return

        for idx, sess in enumerate(s['sessions']):
            row = BoxLayout(orientation='horizontal',
                            size_hint_y=None, height=64, spacing=4)
            start = sess.get('start')
            end = sess.get('end')
            if start and end:
                time_part = f"{start}–{end}"
            else:
                time_part = '—'
            # Używamy Buttona jako "karty" – ma jasne tło, więc ciemny tekst
            # jest dobrze czytelny (Label na domyślnym tle Kivy znika).
            lbl = Button(
                text=(f"{sess['date']}   {time_part}   "
                      f"{sess['hours']:.2f} h"),
                halign='left', valign='middle',
                size_hint_x=0.82,
                font_size='17sp',
                background_normal='',
                background_color=(0.95, 0.95, 0.97, 1),
                color=(0.1, 0.1, 0.1, 1),
            )
            lbl.bind(size=lambda b, *a: setattr(b, 'text_size', (b.width - 12, None)))
            del_b = Button(
                text='X', size_hint_x=0.18, font_size='20sp', bold=True,
                background_normal='', background_color=(0.8, 0.25, 0.25, 1)
            )
            desc = f"{sess['date']}   {time_part}   {sess['hours']:.2f} h"
            del_b.bind(on_release=lambda b, i=idx, d=desc:
                       self.confirm_delete_session(i, d))
            row.add_widget(lbl)
            row.add_widget(del_b)
            cont.add_widget(row)

    def confirm_delete_session(self, idx, desc):
        content = BoxLayout(orientation='vertical', spacing=10, padding=10)
        lbl = Label(
            text=f'Usunąć tę jazdę?\n\n{desc}',
            halign='center', valign='middle', font_size='17sp',
        )
        lbl.bind(size=lambda w, *a: setattr(w, 'text_size', w.size))
        content.add_widget(lbl)
        btns = BoxLayout(size_hint_y=None, height=60, spacing=6)
        no = Button(text='Anuluj', font_size='18sp')
        yes = Button(text='Usuń', font_size='18sp', bold=True,
                     background_normal='',
                     background_color=(0.8, 0.25, 0.25, 1))
        btns.add_widget(no)
        btns.add_widget(yes)
        content.add_widget(btns)
        popup = Popup(title='Potwierdź', content=content,
                      size_hint=(0.88, 0.45), title_size='18sp')
        yes.bind(on_release=lambda *_: (
            self.delete_session(idx), popup.dismiss()))
        no.bind(on_release=popup.dismiss)
        popup.open()

    def delete_session(self, idx):
        app = App.get_running_app()
        app.store.remove_session(app.current_student_id, idx)
        self.refresh()

    def add_session_popup(self):
        app = App.get_running_app()
        if app.store.total(app.current_student_id) >= REQUIRED_HOURS:
            show_info(
                f'Kursant ma już komplet {REQUIRED_HOURS} h.\n'
                f'Nie można dopisać kolejnej jazdy.'
            )
            return

        content = BoxLayout(orientation='vertical', spacing=6, padding=10)
        today = datetime.now().strftime('%Y-%m-%d')
        date_in = Spinner(
            text=today, values=date_choices(since=SCHOOL_START_DATE, ahead=14),
            size_hint_y=None, height=58, font_size='18sp', sync_height=True,
            background_normal='', background_color=(0.92, 0.92, 0.95, 1),
            color=(0.1, 0.1, 0.1, 1),
        )

        times_row = BoxLayout(size_hint_y=None, height=58, spacing=6)
        start_in = Spinner(
            text='08:00', values=HOUR_CHOICES,
            font_size='20sp', sync_height=True,
            background_normal='', background_color=(0.92, 0.92, 0.95, 1),
            color=(0.1, 0.1, 0.1, 1),
        )
        end_in = Spinner(
            text='10:00', values=HOUR_CHOICES,
            font_size='20sp', sync_height=True,
            background_normal='', background_color=(0.92, 0.92, 0.95, 1),
            color=(0.1, 0.1, 0.1, 1),
        )
        times_row.add_widget(start_in)
        times_row.add_widget(end_in)

        summary = Label(
            text='', size_hint_y=None, height=30, font_size='17sp',
            bold=True, color=(0.2, 0.5, 0.2, 1),
        )
        msg = Label(text='', size_hint_y=None, height=30,
                    font_size='15sp', color=(0.8, 0.2, 0.2, 1))

        def update_summary(*_):
            st = parse_hhmm(start_in.text)
            en = parse_hhmm(end_in.text)
            if st and en:
                h = hours_between(st, en)
                summary.text = f'Czas jazdy: {h:.2f} h'
            else:
                summary.text = ''

        start_in.bind(text=update_summary)
        end_in.bind(text=update_summary)
        update_summary()

        btns = BoxLayout(size_hint_y=None, height=60, spacing=6)
        cancel = Button(text='Anuluj', font_size='18sp')
        save = Button(text='Zapisz', font_size='18sp', bold=True,
                      background_normal='',
                      background_color=(0.2, 0.7, 0.3, 1))
        btns.add_widget(cancel)
        btns.add_widget(save)

        content.add_widget(Label(text='Data (RRRR-MM-DD):',
                                 size_hint_y=None, height=28,
                                 font_size='16sp'))
        content.add_widget(date_in)
        content.add_widget(Label(text='Godzina rozpoczęcia / zakończenia:',
                                 size_hint_y=None, height=28,
                                 font_size='16sp'))
        content.add_widget(times_row)
        content.add_widget(summary)
        content.add_widget(msg)
        content.add_widget(btns)

        popup = Popup(title='Nowa jazda', content=content,
                      size_hint=(0.96, 0.85), title_size='18sp')

        def do_save(*_):
            try:
                datetime.strptime(date_in.text.strip(), '%Y-%m-%d')
            except Exception:
                msg.text = 'Data: RRRR-MM-DD'
                return
            st = parse_hhmm(start_in.text)
            en = parse_hhmm(end_in.text)
            if not st or not en:
                msg.text = 'Godziny w formacie HH:MM.'
                return
            h = hours_between(st, en)
            if h <= 0:
                msg.text = 'Godzina zakończenia musi być po rozpoczęciu.'
                return
            if h > 12:
                msg.text = 'Jazda > 12 h — sprawdź godziny.'
                return
            app = App.get_running_app()
            app.store.add_session(
                app.current_student_id,
                date_in.text.strip(),
                start_in.text.strip(),
                end_in.text.strip(),
            )
            popup.dismiss()
            self.refresh()

        save.bind(on_release=do_save)
        cancel.bind(on_release=popup.dismiss)
        popup.open()

    def exam_popup(self):
        app = App.get_running_app()
        student = app.store.get(app.current_student_id)
        if student and student.get('exam'):
            ex = student['exam']
            status = 'zdany' if ex.get('passed') else 'niezdany'
            show_info(
                f'Egzamin został już zapisany jako {status}.\n'
                f'Data: {ex.get("date", "—")}\n\n'
                f'Nie można nadpisać wyniku.'
            )
            return

        content = BoxLayout(orientation='vertical', spacing=8, padding=10)
        today = datetime.now().strftime('%Y-%m-%d')
        date_in = Spinner(
            text=today, values=date_choices(since=SCHOOL_START_DATE, ahead=14),
            size_hint_y=None, height=58, font_size='18sp', sync_height=True,
            background_normal='', background_color=(0.92, 0.92, 0.95, 1),
            color=(0.1, 0.1, 0.1, 1),
        )

        content.add_widget(Label(
            text=f'Egzamin trwa {EXAM_DURATION} min.',
            size_hint_y=None, height=34, font_size='17sp'))
        content.add_widget(Label(text='Data egzaminu:',
                                 size_hint_y=None, height=28, font_size='16sp'))
        content.add_widget(date_in)

        btns = BoxLayout(size_hint_y=None, height=62, spacing=6)
        cancel = Button(text='Anuluj', font_size='17sp')
        fail = Button(text='Niezdany', font_size='17sp', bold=True,
                      background_normal='', background_color=(0.8, 0.25, 0.25, 1))
        passb = Button(text='Zdany', font_size='17sp', bold=True,
                       background_normal='', background_color=(0.2, 0.7, 0.3, 1))
        btns.add_widget(cancel)
        btns.add_widget(fail)
        btns.add_widget(passb)
        content.add_widget(btns)

        popup = Popup(title='Egzamin', content=content,
                      size_hint=(0.94, 0.6), title_size='18sp')
        app = App.get_running_app()
        sid = app.current_student_id

        passb.bind(on_release=lambda *_: (
            app.store.set_exam(sid, True, date_in.text.strip()),
            popup.dismiss(), self.refresh()))
        fail.bind(on_release=lambda *_: (
            app.store.set_exam(sid, False, date_in.text.strip()),
            popup.dismiss(), self.refresh()))
        cancel.bind(on_release=popup.dismiss)
        popup.open()


# -------- Aplikacja --------

class DrivingSchoolApp(App):
    def build(self):
        self.title = 'Nauka jazdy'
        self.current_student_id = None
        path = os.path.join(self.user_data_dir, 'kursanci.json')
        self.store = DataStore(path)
        return Builder.load_string(KV)


if __name__ == '__main__':
    # Na komputerze pokaż okno o rozmiarze iPhone 8 (375x667)
    if platform not in ('ios', 'android'):
        Window.size = (375, 667)
    DrivingSchoolApp().run()