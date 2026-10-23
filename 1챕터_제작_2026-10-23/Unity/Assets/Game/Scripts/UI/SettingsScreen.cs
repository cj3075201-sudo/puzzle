using System;
using System.Collections.Generic;
using System.Linq;
using OUAT.Core;
using UnityEngine;
using UnityEngine.UIElements;

namespace OUAT.UI
{
    /// <summary>
    /// 잠시 멈춤(Esc): 종이 한 장에 손으로 쓴 줄 — 계속하기 / 설정 / 조작 안내 / 처음 화면으로 / 게임 끝내기(확인).
    /// 열려 있는 동안 Time.timeScale = 0(UIRoot가 관리).
    /// </summary>
    public class PauseScreen : VisualElement
    {
        readonly VisualElement sheet, list, confirm;
        readonly Label confirmText;
        Action confirmYes;
        public Action Resume, OpenSettings, OpenControls, ToTitle, Quit;

        public bool IsOpen => style.display == DisplayStyle.Flex;

        public PauseScreen()
        {
            AddToClassList("screen"); AddToClassList("pause-screen");
            pickingMode = PickingMode.Position;
            style.display = DisplayStyle.None;
            Add(UIKit.Box("vignette"));
            sheet = UIKit.Box("pause-sheet", PickingMode.Position); Add(sheet);
            UIKit.Rotate(sheet, -1.4f);
            sheet.Add(UIKit.Box("tape tape-top"));
            sheet.Add(UIKit.Text("잠시 멈춤", "pause-title", Face.SerifBold));
            sheet.Add(UIKit.Box("pause-title-line"));
            list = UIKit.Box("pause-list"); sheet.Add(list);
            list.Add(Item("계속하기", () => Resume?.Invoke(), true));
            list.Add(Item("설정", () => OpenSettings?.Invoke(), false));
            list.Add(Item("조작 안내", () => OpenControls?.Invoke(), false));
            list.Add(Item("처음 화면으로", () => Ask("처음 화면으로 돌아갈까?\n지금까지 한 것은 저장된다.", () => ToTitle?.Invoke()), false));
            list.Add(Item("게임 끝내기", () => Ask("게임을 끝낼까?\n지금까지 한 것은 저장된다.", () => Quit?.Invoke()), false));
            confirm = UIKit.Box("pause-confirm"); sheet.Add(confirm);
            confirmText = UIKit.Text("", "pause-confirm-text", Face.Hand); confirm.Add(confirmText);
            var row = UIKit.Box("pause-confirm-row"); confirm.Add(row);
            row.Add(UIKit.BrushButton("그래", () => { var a = confirmYes; confirmYes = null; a?.Invoke(); }, red: true, extra: "brush-small"));
            row.Add(UIKit.InkButton("아니", CancelAskVoid));
            confirm.style.display = DisplayStyle.None;
        }

        static VisualElement Item(string text, Action a, bool primary)
        {
            var b = UIKit.OnClick(UIKit.Box("menu-item pause-item" + (primary ? " menu-primary" : "")), () => { AudioHub.Play("page", 0.35f, 1.2f); a?.Invoke(); });
            b.Add(UIKit.Box("menu-mark"));
            b.Add(UIKit.Text(text, "menu-label", Face.SerifBold));
            b.Add(UIKit.Box("menu-line"));
            return b;
        }

        void Ask(string q, Action yes)
        {
            confirmText.text = q; confirmYes = yes;
            list.style.display = DisplayStyle.None;
            confirm.style.display = DisplayStyle.Flex;
            UIKit.AnimateIn(confirm, "note-start", 20);
        }

        public bool CancelAsk()
        {
            if (confirm.style.display != DisplayStyle.Flex) return false;
            confirm.style.display = DisplayStyle.None; list.style.display = DisplayStyle.Flex; confirmYes = null;
            return true;
        }

        void CancelAskVoid() => CancelAsk();

        public void Open()
        {
            CancelAsk();
            style.display = DisplayStyle.Flex;
            UIKit.AnimateIn(sheet, "page-start", 20);
            AudioHub.Play("page", 0.5f);
        }

        public void Close() { CancelAsk(); style.display = DisplayStyle.None; }
    }

    /// <summary>
    /// 설정 공책: 왼쪽 쪽에 장(화면·소리·게임·조작), 오른쪽 쪽에 항목. 소리·게임·밝기·수직 동기화·품질 등은 바로 적용,
    /// 해상도·화면 모드는 「적용」 뒤 10초 안에 「유지」를 누르지 않으면 되돌린다.
    /// </summary>
    public class SettingsScreen : VisualElement
    {
        public enum Tab { Display, Sound, Game, Controls }
        readonly VisualElement spread, tabs, rows, footer, applyBtn, keepNote;
        readonly Label tabNote, keepText;
        Tab tab;
        Action onClose;
        // 화면 — 적용 전 값
        int pendRes; FullScreenMode pendMode; List<Vector2Int> resList;
        // 되돌리기 대기
        Vector2Int prevRes; FullScreenMode prevMode; IVisualElementScheduledItem countdown; int left;

        public bool IsOpen => style.display == DisplayStyle.Flex;

        public SettingsScreen()
        {
            AddToClassList("screen"); AddToClassList("settings-screen");
            pickingMode = PickingMode.Position;
            style.display = DisplayStyle.None;
            Add(UIKit.Box("vignette"));
            spread = UIKit.Box("set-spread", PickingMode.Position); Add(spread);
            var leftPage = UIKit.Box("set-left"); spread.Add(leftPage);
            leftPage.Add(UIKit.Text("설정", "set-title", Face.SerifBold));
            leftPage.Add(UIKit.Box("set-title-line"));
            tabs = UIKit.Box("set-tabs"); leftPage.Add(tabs);
            tabNote = UIKit.Text("", "set-tab-note", Face.Hand); leftPage.Add(tabNote);
            var reset = UIKit.InkButton("기본값으로 되돌리기", ResetTab, "set-reset"); leftPage.Add(reset);

            var rightPage = UIKit.Box("set-right"); spread.Add(rightPage);
            rows = UIKit.Box("set-rows"); rightPage.Add(rows);
            footer = UIKit.Box("set-footer"); rightPage.Add(footer);
            applyBtn = UIKit.BrushButton("적용", ApplyDisplay, red: true, extra: "brush-small set-apply");
            footer.Add(applyBtn);
            footer.Add(UIKit.BrushButton("닫기", () => Back(), red: false, extra: "brush-small"));
            spread.Add(UIKit.OnClick(UIKit.Box("close-x set-close"), () => Back()));

            keepNote = UIKit.Box("keep-note", PickingMode.Position); Add(keepNote);
            keepNote.Add(UIKit.Box("tape tape-top"));
            keepText = UIKit.Text("", "keep-text", Face.Hand); keepNote.Add(keepText);
            var kr = UIKit.Box("pause-confirm-row"); keepNote.Add(kr);
            kr.Add(UIKit.BrushButton("유지", KeepDisplay, red: true, extra: "brush-small"));
            kr.Add(UIKit.InkButton("되돌리기", RevertDisplay));
            keepNote.style.display = DisplayStyle.None;
        }

        public void Open(Tab start, Action closed)
        {
            GameSettings.EnsureLoaded();
            onClose = closed;
            resList = GameSettings.Resolutions();
            var cur = new Vector2Int(GameSettings.ResolutionWidth > 0 ? GameSettings.ResolutionWidth : Screen.width, GameSettings.ResolutionHeight > 0 ? GameSettings.ResolutionHeight : Screen.height);
            pendRes = Mathf.Max(0, resList.IndexOf(cur));
            pendMode = GameSettings.ScreenMode;
            style.display = DisplayStyle.Flex;
            SetTab(start);
            UIKit.AnimateIn(spread, "jr-start", 20);
            AudioHub.Play("page", 0.5f);
        }

        /// <summary>Esc·닫기: 되돌리기 대기 중이면 되돌리고, 아니면 저장하고 닫는다.</summary>
        public void Back()
        {
            if (keepNote.style.display == DisplayStyle.Flex) { RevertDisplay(); return; }
            GameSettings.Save();
            style.display = DisplayStyle.None;
            var cb = onClose; onClose = null;
            cb?.Invoke();
        }

        void SetTab(Tab t)
        {
            tab = t;
            tabs.Clear();
            foreach (Tab x in Enum.GetValues(typeof(Tab)))
            {
                var name = x == Tab.Display ? "화면" : x == Tab.Sound ? "소리" : x == Tab.Game ? "게임" : "조작";
                var b = UIKit.OnClick(UIKit.Box("menu-item set-tab" + (x == tab ? " menu-primary set-tab-on" : "")), () => { AudioHub.Play("page", 0.3f, 1.3f); SetTab(x); });
                b.Add(UIKit.Box("menu-mark"));
                b.Add(UIKit.Text(name, "menu-label", Face.SerifBold));
                b.Add(UIKit.Box("menu-line"));
                tabs.Add(b);
            }
            tabNote.text = tab == Tab.Display ? "해상도·화면 모드는 「적용」을 눌러야 바뀐다.\n나머지는 바로 바뀐다."
                         : tab == Tab.Sound ? "움직이는 동안 바로 들린다."
                         : tab == Tab.Game ? "말풍선·생각·알림 같은 세계 위 글자에 적용된다."
                         : "";
            BuildRows();
        }

        void BuildRows()
        {
            rows.Clear();
            applyBtn.style.display = DisplayStyle.None;
            switch (tab)
            {
                case Tab.Display: BuildDisplay(); break;
                case Tab.Sound: BuildSound(); break;
                case Tab.Game: BuildGame(); break;
                case Tab.Controls: BuildControls(); break;
            }
            UIKit.AnimateIn(rows, "detail-start", 20);
        }

        // ── 줄 만들기 ──
        VisualElement Row(string label, VisualElement control, string note = null, bool enabled = true)
        {
            var r = UIKit.Box("set-row");
            var main = UIKit.Box("set-row-main"); r.Add(main);
            main.Add(UIKit.Text(label, "set-label", Face.Serif));
            main.Add(control);
            if (!string.IsNullOrEmpty(note)) r.Add(UIKit.Text(note, "set-note", Face.Hand));
            if (!enabled) { r.AddToClassList("set-row-off"); r.SetEnabled(false); }
            rows.Add(r);
            return r;
        }

        static VisualElement Choices(string[] names, int selected, Action<int> pick)
        {
            var box = UIKit.Box("set-choices");
            for (int i = 0; i < names.Length; i++)
            {
                int k = i;
                var c = UIKit.OnClick(UIKit.Box("set-choice" + (i == selected ? " set-choice-on" : "")), () =>
                {
                    foreach (var ch in box.Children()) ch.RemoveFromClassList("set-choice-on");
                    box[k].AddToClassList("set-choice-on");
                    AudioHub.Play("piece", 0.35f, 1.3f);
                    pick(k);
                });
                c.Add(UIKit.Box("set-choice-ring"));
                c.Add(UIKit.Text(names[i], "set-choice-text", Face.Hand));
                box.Add(c);
            }
            return box;
        }

        VisualElement Stepper(Func<string> text, Action<int> step)
        {
            var box = UIKit.Box("set-stepper");
            var val = UIKit.Text(text(), "set-step-value", Face.Hand);
            box.Add(UIKit.OnClick(UIKit.Text("‹", "set-step-arrow", Face.Serif), () => { step(-1); val.text = text(); AudioHub.Play("piece", 0.3f, 1.2f); }));
            box.Add(val);
            box.Add(UIKit.OnClick(UIKit.Text("›", "set-step-arrow", Face.Serif), () => { step(1); val.text = text(); AudioHub.Play("piece", 0.3f, 1.2f); }));
            return box;
        }

        // ── 화면 ──
        void BuildDisplay()
        {
            Row("해상도", Stepper(() => resList.Count == 0 ? "-" : $"{resList[pendRes].x} × {resList[pendRes].y}" + (IsCurrentRes(pendRes) ? "  (지금)" : ""),
                d => { pendRes = Mathf.Clamp(pendRes + d, 0, Mathf.Max(0, resList.Count - 1)); UpdateApply(); }));
            var modes = new[] { FullScreenMode.ExclusiveFullScreen, FullScreenMode.FullScreenWindow, FullScreenMode.Windowed };
            Row("화면 모드", Choices(new[] { "전체 화면", "테두리 없는 창", "창 모드" }, Mathf.Max(0, Array.IndexOf(modes, pendMode)),
                i => { pendMode = modes[i]; UpdateApply(); }));
            Row("수직 동기화", Choices(new[] { "켜기", "끄기" }, GameSettings.VSync ? 0 : 1,
                i => { GameSettings.VSync = i == 0; GameSettings.ApplyGraphics(); GameSettings.Save(); BuildRows(); }), "화면 찢김을 막음 — 모니터 주사율에 맞춤");
            int fi = Array.IndexOf(GameSettings.FrameLimits, GameSettings.FrameLimit); if (fi < 0) fi = 1;
            Row("최대 프레임", Choices(new[] { "30", "60", "120", "144", "무제한" }, fi,
                i => { GameSettings.FrameLimit = GameSettings.FrameLimits[i]; GameSettings.ApplyGraphics(); GameSettings.Save(); }),
                GameSettings.VSync ? "수직 동기화가 켜져 있으면 모니터 주사율을 따른다" : null, enabled: !GameSettings.VSync);
            Row("그래픽 품질", Choices(new[] { "낮음", "보통", "높음" }, GameSettings.Quality,
                i => { GameSettings.Quality = i; GameSettings.ApplyGraphics(); GameSettings.Save(); }), "그림자 거리·계단 현상 정리");
            Row("렌더 배율", new InkSlider(GameSettings.RenderScale, 0.5f, 1f, v => $"{Mathf.RoundToInt(v * 100)}%",
                v => { GameSettings.RenderScale = Mathf.Round(v * 20f) / 20f; GameSettings.ApplyGraphics(); }, () => GameSettings.Save()), "낮추면 빨라지고 조금 흐려진다");
            Row("밝기", new InkSlider(GameSettings.Brightness, -0.3f, 0.3f, v => v > 0.01f ? "밝게" : v < -0.01f ? "어둡게" : "기본",
                v => { GameSettings.Brightness = v; GameSettings.NotifyChanged(); }, () => GameSettings.Save()));
            UpdateApply();
        }

        bool IsCurrentRes(int i) => resList != null && i >= 0 && i < resList.Count && resList[i].x == GameSettings.ResolutionWidth && resList[i].y == GameSettings.ResolutionHeight;

        void UpdateApply()
        {
            bool changed = resList != null && resList.Count > 0 && (!IsCurrentRes(pendRes) || pendMode != GameSettings.ScreenMode);
            applyBtn.style.display = tab == Tab.Display && changed ? DisplayStyle.Flex : DisplayStyle.None;
        }

        void ApplyDisplay()
        {
            if (resList == null || resList.Count == 0) return;
            prevRes = new Vector2Int(GameSettings.ResolutionWidth, GameSettings.ResolutionHeight);
            prevMode = GameSettings.ScreenMode;
            GameSettings.ResolutionWidth = resList[pendRes].x; GameSettings.ResolutionHeight = resList[pendRes].y;
            GameSettings.ScreenMode = pendMode;
            GameSettings.ApplyResolution();
            applyBtn.style.display = DisplayStyle.None;
            left = 10;
            keepText.text = $"이 화면으로 둘까?\n{left}초 뒤 원래대로 돌아간다.";
            keepNote.style.display = DisplayStyle.Flex;
            UIKit.AnimateIn(keepNote, "note-start", 20);
            countdown?.Pause();
            countdown = schedule.Execute(() =>
            {
                left--;
                keepText.text = $"이 화면으로 둘까?\n{Mathf.Max(0, left)}초 뒤 원래대로 돌아간다.";
                if (left <= 0) RevertDisplay();
            }).Every(1000).StartingIn(1000);
        }

        void KeepDisplay()
        {
            countdown?.Pause(); countdown = null;
            keepNote.style.display = DisplayStyle.None;
            GameSettings.Save();
            BuildRows();
        }

        void RevertDisplay()
        {
            countdown?.Pause(); countdown = null;
            keepNote.style.display = DisplayStyle.None;
            if (prevRes.x > 0) { GameSettings.ResolutionWidth = prevRes.x; GameSettings.ResolutionHeight = prevRes.y; }
            GameSettings.ScreenMode = prevMode;
            GameSettings.ApplyResolution();
            pendRes = Mathf.Max(0, resList.FindIndex(r => r.x == GameSettings.ResolutionWidth && r.y == GameSettings.ResolutionHeight));
            pendMode = GameSettings.ScreenMode;
            GameSettings.Save();
            if (tab == Tab.Display) BuildRows();
        }

        // ── 소리 ──
        void BuildSound()
        {
            Row("전체", Vol(() => GameSettings.MasterVolume, v => GameSettings.MasterVolume = v, "page"));
            Row("음악", Vol(() => GameSettings.MusicVolume, v => GameSettings.MusicVolume = v, null));
            Row("효과음", Vol(() => GameSettings.SfxVolume, v => GameSettings.SfxVolume = v, "piece"));
            Row("환경음", Vol(() => GameSettings.AmbientVolume, v => GameSettings.AmbientVolume = v, null));
        }

        static InkSlider Vol(Func<float> get, Action<float> set, string preview)
        {
            return new InkSlider(get(), 0f, 1f, v => $"{Mathf.RoundToInt(v * 100)}",
                v => { set(v); GameSettings.NotifyChanged(); },
                () => { GameSettings.Save(); if (preview != null) AudioHub.Play(preview, 0.7f); });
        }

        // ── 게임 ──
        void BuildGame()
        {
            Row("화면 흔들림", Choices(new[] { "켜기", "끄기" }, GameSettings.ScreenShake ? 0 : 1, i => { GameSettings.ScreenShake = i == 0; Commit(); }));
            var scales = new[] { 0.9f, 1f, 1.1f, 1.2f, 1.3f };
            int si = Array.FindIndex(scales, s => Mathf.Abs(s - GameSettings.UiScale) < 0.01f); if (si < 0) si = 1;
            Row("글자 크기", Choices(new[] { "90%", "100%", "110%", "120%", "130%" }, si, i => { GameSettings.UiScale = scales[i]; Commit(); }), "세계 위 말풍선·생각·알림 글자");
            Row("커서 크기", Choices(new[] { "보통", "크게" }, GameSettings.CursorLarge ? 1 : 0, i => { GameSettings.CursorLarge = i == 1; Commit(); CursorSet.Refresh(); }));
            int bi = Array.FindIndex(GameSettings.BalloonTimes, s => Mathf.Abs(s - GameSettings.BalloonTime) < 0.01f); if (bi < 0) bi = 1;
            Row("말풍선 표시 시간", Choices(new[] { "짧게", "보통", "길게" }, bi, i => { GameSettings.BalloonTime = GameSettings.BalloonTimes[i]; Commit(); }));
        }

        static void Commit() { GameSettings.Save(); GameSettings.NotifyChanged(); }

        // ── 조작 ──
        void BuildControls()
        {
            foreach (var (k, d) in ControlsList)
            {
                var r = UIKit.Box("set-key-row");
                r.Add(UIKit.Text(k, "set-key", Face.SerifBold));
                r.Add(UIKit.Text(d, "set-key-desc", Face.Hand));
                rows.Add(r);
            }
        }

        public static readonly (string key, string desc)[] ControlsList =
        {
            ("왼쪽 클릭", "걷기 · 말 걸기 · 만지기 · 읽기"),
            ("휠 클릭", "둘레 살피기 — 누를 수 있는 것 표시"),
            ("Tab / J", "기록 공책 열고 닫기"),
            ("Esc", "창 닫기 · 잠시 멈춤"),
            ("글자 누르기", "그 글자의 뜻(짐작)과 메모 적기"),
            ("끌어 놓기", "대화판: 모형을 판에, 글자를 조각에"),
            ("오른쪽 클릭", "대화판: 조각 빼기"),
            ("두 번 누르기", "대화판: 조각의 글자 빼기"),
        };

        void ResetTab()
        {
            AudioHub.Play("page", 0.4f);
            if (tab == Tab.Display) { GameSettings.ResetDefaults(GameSettings.Section.Display); resList = GameSettings.Resolutions(); pendRes = Mathf.Max(0, resList.FindIndex(r => r.x == GameSettings.ResolutionWidth && r.y == GameSettings.ResolutionHeight)); pendMode = GameSettings.ScreenMode; }
            else if (tab == Tab.Sound) GameSettings.ResetDefaults(GameSettings.Section.Sound);
            else if (tab == Tab.Game) { GameSettings.ResetDefaults(GameSettings.Section.Game); CursorSet.Refresh(); }
            BuildRows();
        }
    }

    /// <summary>연필 선 위의 잉크 방울 손잡이 슬라이더. 끄는 동안 change, 놓으면 release.</summary>
    public class InkSlider : VisualElement
    {
        readonly VisualElement track, fill, knob;
        readonly Label value;
        readonly float min, max;
        readonly Func<float, string> fmt;
        readonly Action<float> change;
        readonly Action release;
        float v;
        int pointer = -1;
        const float Width = 380f;

        public InkSlider(float initial, float min, float max, Func<float, string> fmt, Action<float> change, Action release)
        {
            this.min = min; this.max = max; this.fmt = fmt; this.change = change; this.release = release;
            AddToClassList("ink-slider");
            pickingMode = PickingMode.Position;
            track = UIKit.Box("ink-track"); Add(track);
            fill = UIKit.Box("ink-fill"); track.Add(fill);
            fill.Add(UIKit.Box("ink-fill-ink"));
            knob = UIKit.Box("ink-knob"); track.Add(knob);
            value = UIKit.Text("", "ink-value", Face.Hand); Add(value);
            Set(initial, false);
            RegisterCallback<PointerDownEvent>(e => { if (e.button != 0) return; pointer = e.pointerId; this.CapturePointer(pointer); Drag(e.position); e.StopPropagation(); });
            RegisterCallback<PointerMoveEvent>(e => { if (e.pointerId == pointer) Drag(e.position); });
            RegisterCallback<PointerUpEvent>(e => { if (e.pointerId != pointer) return; this.ReleasePointer(pointer); pointer = -1; release?.Invoke(); });
        }

        void Drag(Vector2 panelPos)
        {
            var local = track.WorldToLocal(panelPos);
            Set(Mathf.Lerp(min, max, Mathf.Clamp01(local.x / Width)), true);
        }

        void Set(float x, bool notify)
        {
            v = Mathf.Clamp(x, Mathf.Min(min, max), Mathf.Max(min, max));
            float k = Mathf.InverseLerp(min, max, v);
            fill.style.width = k * Width;
            knob.style.left = k * Width - 13f;
            value.text = fmt != null ? fmt(v) : v.ToString("0.00");
            if (notify) change?.Invoke(v);
        }
    }
}
