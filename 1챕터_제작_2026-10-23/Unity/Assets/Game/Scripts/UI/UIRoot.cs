using System;
using System.Collections;
using System.Collections.Generic;
using System.Linq;
using OUAT.Core;
using OUAT.World;
using UnityEngine;
using UnityEngine.TextCore.Text;
using UnityEngine.UIElements;

namespace OUAT.UI
{
    public enum CursorKind { Default, Talk, Use, Walk }

    /// <summary>
    /// 화면 전체(UI Toolkit, 1920×1080 기준). 층: 세계 위 말(글자 한 줄)·말 걸기 표시 → HUD(목표 쪽지·기록 공책·장소 이름) → 극 대사 →
    /// 연출 띠 → 대화/읽을거리/새김/기록 → 추측 쪽지 → 알림 쪽지 → 확정 도장 → 제목/끝 → 페이드.
    /// 화-11: 세계에서 크리처가 하는 말은 글자만 한 줄(GlyphLine). 직소 판은 대화창(DialogueScreen) 안에서만.
    /// </summary>
    [RequireComponent(typeof(UIDocument))]
    public class UIRoot : MonoBehaviour
    {
        public FontAsset fontRegular, fontBold;
        public StyleSheet styleSheet;

        UIDocument doc;
        VisualElement root, worldLayer, hud, toastLayer, stampLayer, fader, title, ending, stageLine, tooltip, placeBanner, chapterTitle, letterbox, flashback,
            pickPrompt, holdBar, holdFill, belly, goalCard, journalBtn, journalBadge, helpLine, titleMenu, endingGlyphs;
        Label goalText, goalPlace, goalHint, placeLabel, tooltipLabel, journalBadgeLabel, titleSub;
        ReadableScreen readable;
        DecreeScreen decree;
        DialogueScreen dialogue;
        InscriptionScreen inscription;
        JournalScreen journal;
        GuessPopup guessPopup;
        readonly Dictionary<NpcActor, Overhead> overheads = new Dictionary<NpcActor, Overhead>();
        readonly Dictionary<NpcActor, VisualElement> talkMarks = new Dictionary<NpcActor, VisualElement>();
        readonly Dictionary<NpcActor, bool> talkOverride = new Dictionary<NpcActor, bool>();
        readonly HashSet<NpcActor> talkAuto = new HashSet<NpcActor>();
        readonly Queue<string> stampQueue = new Queue<string>();
        bool stamping;
        Game game;
        GameState boundState;
        bool cinematic;
        CursorKind cursorKind;
        float boundAt = -1f;
        int newSeenCount;
        public readonly HashSet<string> NewWords = new HashSet<string>();

        static readonly Queue<(string word, string place)> pendingSee = new Queue<(string, string)>();
        static readonly Queue<string> pendingSentences = new Queue<string>();

        public bool Bound { get; private set; }
        public bool BlocksWorld => pause.IsOpen || settings.IsOpen || decree.IsOpen || dialogue.IsOpen || inscription.IsOpen || journal.IsOpen || guessPopup.IsOpen || readable.IsOpen || title.style.display == DisplayStyle.Flex || ending.style.display == DisplayStyle.Flex;
        /// <summary>세계 위 표시(머리 위 말·말 걸기 표시)를 가리는 창이 열렸나. 대화 중 상대 반응을 보는 동안(Peeking)과 추측 쪽지만 열린 때는 가리지 않는다.</summary>
        bool HidesWorldUI => pause.IsOpen || settings.IsOpen || decree.IsOpen || (dialogue.IsOpen && !dialogue.Peeking) || inscription.IsOpen || journal.IsOpen || readable.IsOpen || title.style.display == DisplayStyle.Flex || ending.style.display == DisplayStyle.Flex;
        public bool PointerOverUI { get; private set; }
        bool AnyScreenOpen => pause.IsOpen || settings.IsOpen || decree.IsOpen || dialogue.IsOpen || inscription.IsOpen || journal.IsOpen || readable.IsOpen || title.style.display == DisplayStyle.Flex || ending.style.display == DisplayStyle.Flex;
        VisualElement pageTurn, pageSheet, pageHeader, brightness;
        PauseScreen pause;
        SettingsScreen settings;
        bool devGoal;           // F2: 개발용 목표 쪽지(기본 꺼짐)
        float savedTimeScale = 1f;
        bool helpShowing;
        const string HelpSeenKey = "ouat_help_seen";
        Label pageNumber, pageName;
        readonly Dictionary<string, int> pageNumbers = new Dictionary<string, int>();
        bool turning;
        string exitLabel;
        readonly Queue<(string head, string text)> pendingToasts = new Queue<(string, string)>();
        float nextToastAt;

        /// <summary>글자 입력 중(추측 쪽지가 열렸거나 입력칸에 포커스). Core는 이때 Tab/J 같은 단축키를 무시한다(QA P1-5).</summary>
        public bool TypingText
        {
            get
            {
                if (guessPopup != null && guessPopup.IsOpen) return true;
                var f = root?.panel?.focusController?.focusedElement as VisualElement;
                return f != null && (f is TextField || f.GetFirstAncestorOfType<TextField>() != null);
            }
        }

        class Overhead
        {
            public VisualElement el, body, card, tail;
            public GlyphLine line;
            public string sentence;
            public float until;
            public bool persistent, removing, placed;
            public float range;
        }

        /// <summary>크리처마다 지금 켜져 있어야 할 상시 말(임시 말이 끝나면 이것으로 돌아간다).</summary>
        readonly Dictionary<NpcActor, string> persistentWanted = new Dictionary<NpcActor, string>();

        void Awake()
        {
            doc = GetComponent<UIDocument>();
            if (!doc.panelSettings) doc.panelSettings = Resources.Load<PanelSettings>("UI/OUAT_PanelSettings");
            root = doc.rootVisualElement;
            root.AddToClassList("ouat-root");
            if (styleSheet == null) styleSheet = Resources.Load<StyleSheet>("UI/ouat");
            if (styleSheet) root.styleSheets.Add(styleSheet);
            if (fontRegular == null) fontRegular = Resources.Load<FontAsset>("UI/Fonts/Pretendard-Regular SDF");
            if (fontBold == null) fontBold = Resources.Load<FontAsset>("UI/Fonts/Pretendard-SemiBold SDF");
            UIKit.SansAsset = fontRegular;
            if (UIKit.HasSerif) UIKit.SetFace(root, Face.Serif);
            else if (fontRegular) root.style.unityFontDefinition = FontDefinition.FromSDFFont(fontRegular);
            root.pickingMode = PickingMode.Ignore;
            Build();
            GameSettings.EnsureLoaded();
            GameSettings.Changed += OnSettingsChanged;
            OnSettingsChanged();
        }

        void OnDestroy()
        {
            GameSettings.Changed -= OnSettingsChanged;
            if (Time.timeScale == 0f) Time.timeScale = 1f;
        }

        void Build()
        {
            brightness = Layer("brightness");   // 밝기 설정: 세계만 덮는 얇은 막(글자 UI보다 아래)
            worldLayer = Layer("world-layer");
            BuildHud();

            stageLine = Layer("stage-line"); stageLine.style.display = DisplayStyle.None;

            letterbox = Layer("letterbox");
            letterbox.Add(UIKit.Box("lb-band lb-top"));
            letterbox.Add(UIKit.Box("lb-band lb-bottom"));
            flashback = Layer("flashback"); flashback.style.display = DisplayStyle.None;

            pickPrompt = Layer("pick-prompt");
            var pickNote = UIKit.Box("pick-note");
            pickNote.Add(UIKit.Text("줄 선 주민 가운데 하나를 짚는다", "pick-text", Face.Hand));
            pickPrompt.Add(pickNote);
            pickPrompt.Add(UIKit.Box("pick-arrow"));
            pickPrompt.style.display = DisplayStyle.None;

            holdBar = Layer("hold-bar");
            var holdTrack = UIKit.Box("hold-track"); holdBar.Add(holdTrack);
            holdFill = UIKit.Box("hold-fill"); holdTrack.Add(holdFill);
            holdFill.Add(UIKit.Box("hold-ink"));
            holdBar.style.display = DisplayStyle.None;

            dialogue = new DialogueScreen(this); root.Add(dialogue);
            readable = new ReadableScreen(); root.Add(readable);
            decree = new DecreeScreen(); root.Add(decree);
            inscription = new InscriptionScreen(this); root.Add(inscription);
            journal = new JournalScreen(this); root.Add(journal);
            guessPopup = new GuessPopup(); root.Add(guessPopup);
            pause = new PauseScreen
            {
                Resume = ClosePause,
                OpenSettings = () => OpenSettings(SettingsScreen.Tab.Display),
                OpenControls = () => OpenSettings(SettingsScreen.Tab.Controls),
                ToTitle = () => { SaveIfSafe(); Time.timeScale = 1f; UnityEngine.SceneManagement.SceneManager.LoadScene(0); },
                Quit = () => { SaveIfSafe(); Time.timeScale = 1f; Application.Quit(); }
            };
            root.Add(pause);
            settings = new SettingsScreen(); root.Add(settings);

            toastLayer = Layer("toast-layer");
            stampLayer = Layer("stamp-layer");
            tooltip = Layer("tooltip"); tooltipLabel = UIKit.Text("", "tooltip-text", Face.Hand); tooltip.Add(tooltipLabel); tooltip.style.display = DisplayStyle.None;
            belly = Layer("belly"); belly.style.display = DisplayStyle.None;   // 장 제목·끝 화면보다 아래(QA P0-1)
            pageHeader = Layer("page-header");
            var pageStrip = UIKit.Box("page-strip"); pageHeader.Add(pageStrip);
            UIKit.Rotate(pageStrip, 0.6f);
            pageNumber = UIKit.Text("", "page-number", Face.Serif); pageStrip.Add(pageNumber);
            pageName = UIKit.Text("", "page-name", Face.SerifBold); pageStrip.Add(pageName);
            pageStrip.Add(UIKit.Box("page-rule"));
            pageHeader.style.display = DisplayStyle.None;
            pageTurn = Layer("page-turn");
            pageSheet = UIKit.Box("page-sheet"); pageTurn.Add(pageSheet);
            pageSheet.Add(UIKit.Box("page-sheet-paper"));
            pageSheet.Add(UIKit.Box("page-curl"));
            pageTurn.style.display = DisplayStyle.None;
            chapterTitle = Layer("chapter-title"); chapterTitle.style.display = DisplayStyle.None;

            title = BuildTitle(); root.Add(title);
            ending = BuildEnding(); root.Add(ending);
            settings.PlaceInFront(ending);   // 제목 화면에서 열어도 위에 오게
            fader = Layer("fader"); fader.style.opacity = 0;

            root.RegisterCallback<PointerMoveEvent>(e => { tooltip.style.left = e.position.x + 22; tooltip.style.top = e.position.y + 20; }, TrickleDown.TrickleDown);
        }

        VisualElement Layer(string cls)
        {
            var v = new VisualElement { pickingMode = PickingMode.Ignore };
            v.AddToClassList("layer"); UIKit.AddClasses(v, cls);
            root.Add(v);
            return v;
        }

        void BuildHud()
        {
            hud = Layer("hud");
            goalCard = UIKit.Box("goal-card");
            UIKit.Rotate(goalCard, -0.8f);
            hud.Add(goalCard);
            var stub = UIKit.Box("goal-stub"); stub.Add(UIKit.Box("goal-icon")); goalCard.Add(stub);
            var col = UIKit.Box("goal-col"); goalCard.Add(col);
            goalPlace = UIKit.Text("", "goal-place", Face.Serif); col.Add(goalPlace);
            goalText = UIKit.Text("", "goal-text", Face.SerifBold); col.Add(goalText);
            goalHint = UIKit.Text("", "goal-hint", Face.Hand); col.Add(goalHint);
            goalCard.style.display = DisplayStyle.None;

            journalBtn = UIKit.OnClick(UIKit.Box("journal-btn"), () => ToggleJournal());
            journalBtn.Add(UIKit.Box("journal-icon"));
            journalBtn.Add(UIKit.Text("기록", "journal-label", Face.Hand));
            journalBtn.Add(UIKit.Text("Tab", "journal-key", Face.Serif));
            journalBadge = UIKit.Box("journal-badge");
            journalBadgeLabel = UIKit.Text("", "journal-badge-text", Face.Hand);
            journalBadge.Add(journalBadgeLabel);
            journalBadge.style.display = DisplayStyle.None;
            journalBtn.Add(journalBadge);
            hud.Add(journalBtn);

            // 처음 조작 안내: 왼쪽 아래 찢은 쪽지(마우스 그림 + 손글씨 두 줄). 처음으로 세계를 눌러 걷거나 말을 걸면 사라진다.
            helpLine = UIKit.Box("help-note");
            UIKit.Rotate(helpLine, -1.4f);
            helpLine.Add(UIKit.Box("help-mouse"));
            var helpCol = UIKit.Box("help-col"); helpLine.Add(helpCol);
            helpCol.Add(UIKit.Text("눌러서 걷고, 말을 건다", "help-main", Face.Hand));
            helpCol.Add(UIKit.Text("휠 — 둘레 살피기  ·  Tab — 기록", "help-sub", Face.Hand));
            hud.Add(helpLine);

            placeBanner = UIKit.Box("place-banner");
            var placeStrip = UIKit.Box("place-strip"); placeBanner.Add(placeStrip);
            UIKit.Rotate(placeStrip, -0.8f);
            placeLabel = UIKit.Text("", "place-name", Face.SerifBold);
            placeStrip.Add(placeLabel);
            placeStrip.Add(UIKit.Box("place-line"));
            placeStrip.Add(UIKit.Box("tape tape-top"));
            placeBanner.style.display = DisplayStyle.None;
            hud.Add(placeBanner);
            hud.style.display = DisplayStyle.None;
        }

        public void Bind(Game g)
        {
            game = g; Bound = true;
            title.style.display = DisplayStyle.None;
            hud.style.display = DisplayStyle.Flex;
            hud.RemoveFromClassList("hud-hidden");
            if (boundAt < 0)
            {
                boundAt = Time.unscaledTime;
                // 조작 안내 한 줄: 처음 한 번 새 게임의 첫 60초만(그 뒤에는 잠시 멈춤 › 조작 안내)
                helpShowing = !PlayerPrefs.HasKey(HelpSeenKey);
                helpLine.EnableInClassList("help-gone", !helpShowing);
                helpLine.style.display = helpShowing ? DisplayStyle.Flex : DisplayStyle.None;
            }
            if (boundState != g.State)
            {
                if (boundState != null) { boundState.Changed -= OnStateChanged; boundState.WordSeen -= OnWordSeen; }
                boundState = g.State;
                boundState.Changed += OnStateChanged;
                boundState.WordSeen += OnWordSeen;
                newSeenCount = 0; NewWords.Clear(); UpdateBadge();
            }
            g.StateRefreshed -= RefreshTalkMarks;
            g.StateRefreshed += RefreshTalkMarks;
        }

        void OnStateChanged() { if (journal.IsOpen) journal.Refresh(); }

        void OnWordSeen(string w)
        {
            if (journal.IsOpen) return;
            if (NewWords.Add(w)) { newSeenCount++; UpdateBadge(true); }
        }

        void UpdateBadge(bool pulse = false)
        {
            journalBadge.style.display = newSeenCount > 0 ? DisplayStyle.Flex : DisplayStyle.None;
            journalBadgeLabel.text = "+" + newSeenCount;
            if (pulse) UIKit.AnimateIn(journalBadge, "badge-pop", 30);
        }

        /// <summary>처음 조작 안내 쪽지를 접는다(첫 걷기·말 걸기 때 UI가 스스로 부름 — Core가 불러도 됨). 한 번 접으면 다시 안 나옴(PlayerPrefs).</summary>
        public void DismissControlsHint()
        {
            if (!helpShowing) return;
            helpShowing = false;
            helpLine.schedule.Execute(() => helpLine.AddToClassList("help-gone")).StartingIn(700);
            PlayerPrefs.SetInt(HelpSeenKey, 1); PlayerPrefs.Save();
        }

        /// <summary>기록창을 열었다 닫으면 새 글자 표시를 지운다(JournalScreen이 부름).</summary>
        public void ClearNewWords() { NewWords.Clear(); newSeenCount = 0; UpdateBadge(); }

        /// <summary>UI가 문장을 그렸을 때 그 낱말을 “봄”으로 적는다. 상태 변경은 다음 Update로 미뤄 Core의 갱신 중 재진입을 피한다.</summary>
        public static void NoteSeen(string sentenceId, IEnumerable<string> words, string place)
        {
            if (words != null) foreach (var w in words) pendingSee.Enqueue((w, place));
            if (!string.IsNullOrEmpty(sentenceId)) pendingSentences.Enqueue(sentenceId);
        }

        /// <summary>문장을 본 적 있나(기록창 “나온 말”). 깃발 sn:문장id로 저장된다.</summary>
        public static bool SentenceSeen(GameState s, string sentenceId) => s != null && s.Has("sn:" + sentenceId);

        void Update()
        {
            if (game != null)
            {
                while (pendingSee.Count > 0) { var (sw, sp0) = pendingSee.Dequeue(); game.State.See(sw, sp0 ?? PlaceZone.Current); }
                while (pendingSentences.Count > 0) { var s = pendingSentences.Dequeue(); if (!game.State.Has("sn:" + s)) game.State.Set("sn:" + s); }
            }
            else { pendingSee.Clear(); pendingSentences.Clear(); }
            if (root.panel == null) return;
            // UI 위에 마우스가 있나(월드 클릭 막기)
            var p = RuntimePanelUtils.ScreenToPanel(root.panel, new Vector2(Input.mousePosition.x, Screen.height - Input.mousePosition.y));
            var picked = root.panel.Pick(p);
            PointerOverUI = picked != null && picked != root && !picked.ClassListContains("layer");
            ApplyCursor();
            bool screen = AnyScreenOpen;
            toastLayer.style.display = screen ? DisplayStyle.None : DisplayStyle.Flex;
            if (!screen && pendingToasts.Count > 0 && Time.unscaledTime >= nextToastAt)
            {
                var (th, tt) = pendingToasts.Dequeue();
                nextToastAt = Time.unscaledTime + 0.6f;
                Toast(th, tt, false);
            }
            // 처음 조작 안내: 세계를 처음 눌렀을 때(걷기·말 걸기) 사라짐. 창·연출 중에는 숨김.
            if (helpShowing)
            {
                bool calm = !AnyScreenOpen && !cinematic && (game == null || !game.Busy);
                helpLine.style.display = calm ? DisplayStyle.Flex : DisplayStyle.None;
                if (calm && Input.GetMouseButtonDown(0) && !PointerOverUI) DismissControlsHint();
            }
            if (Input.GetKeyDown(KeyCode.F2) && Bound) { devGoal = !devGoal; goalCard.style.display = devGoal && !string.IsNullOrEmpty(goalText.text) ? DisplayStyle.Flex : DisplayStyle.None; }
            UpdateWorldUI();
        }

        // ── 제목·끝 ──────────────────────────────────────
        VisualElement BuildTitle()
        {
            var t = UIKit.Box("screen title-screen", PickingMode.Position);
            var art = Resources.Load<Texture2D>("Pictures/title_art");
            if (art) { var img = new Image { image = art, scaleMode = ScaleMode.ScaleAndCrop, pickingMode = PickingMode.Ignore }; img.AddToClassList("title-art"); t.Add(img); }
            t.Add(UIKit.Box("vignette"));
            var box = UIKit.Box("title-box"); t.Add(box);
            box.Add(UIKit.Text("Once Under a Time", "title-name", Face.SerifBold));
            box.Add(UIKit.Box("title-line"));
            titleSub = UIKit.Text("1장", "title-sub", Face.Serif); box.Add(titleSub);
            box.Add(UIKit.Text("낯선 글자를 짐작하고, 조각을 맞춰 말을 거는 미완성 그림책 속 언어 퍼즐 모험", "title-tagline", Face.Serif));
            titleMenu = UIKit.Box("title-menu"); t.Add(titleMenu);
            t.Add(UIKit.Text("세라테 · 2026 졸업 프로젝트 시험판", "title-foot", Face.Serif));
            return t;
        }

        VisualElement MenuItem(string text, Action a, bool primary, bool final = true)
        {
            var b = UIKit.OnClick(UIKit.Box("menu-item" + (primary ? " menu-primary" : "")), () =>
            {
                if (title.pickingMode == PickingMode.Ignore) return;
                if (final) { title.pickingMode = PickingMode.Ignore; titleMenu.SetEnabled(false); }
                a?.Invoke();
            });
            b.Add(UIKit.Box("menu-mark"));
            b.Add(UIKit.Text(text, "menu-label", Face.SerifBold));
            b.Add(UIKit.Box("menu-line"));
            return b;
        }

        public void ShowTitle(bool hasSave, Action newGame, Action cont)
        {
            title.style.display = DisplayStyle.Flex;
            title.pickingMode = PickingMode.Position; titleMenu.SetEnabled(true);
            var village = Game.I != null && Game.I.Data != null && !string.IsNullOrEmpty(Game.I.Data.VillageName) ? Game.I.Data.VillageName : "미완성 마을";
            titleSub.text = "1장 · " + village;
            titleMenu.Clear();
            if (hasSave) titleMenu.Add(MenuItem("이어서 하기", () => { AudioHub.Play("page"); cont(); }, true));
            titleMenu.Add(MenuItem("처음부터", () => { AudioHub.Play("page"); newGame(); }, !hasSave));
            titleMenu.Add(MenuItem("설정", () => { AudioHub.Play("page", 0.4f); OpenSettings(SettingsScreen.Tab.Display); }, false, final: false));
            titleMenu.Add(MenuItem("그만하기", Application.Quit, false));
            int i = 0;
            foreach (var c in titleMenu.Children()) UIKit.AnimateIn(c, "menu-start", 200 + 120 * i++);
        }

        VisualElement BuildEnding()
        {
            var t = UIKit.Box("screen ending-screen", PickingMode.Position);
            t.style.display = DisplayStyle.None;
            t.Add(UIKit.Box("vignette"));
            var box = UIKit.Box("ending-box"); t.Add(box);
            box.Add(UIKit.Text("1장 끝", "ending-small", Face.Serif));
            box.Add(UIKit.Text("물고기 뱃속으로", "ending-big", Face.SerifBold));
            box.Add(UIKit.Box("title-line"));
            box.Add(UIKit.Text("키노피오와 함께, 다음 장으로 이어진다.", "ending-line", Face.Serif));
            endingGlyphs = UIKit.Box("ending-glyphs"); box.Add(endingGlyphs);
            box.Add(UIKit.InkButton("처음 화면으로", () => { GameState.DeleteSave(); UnityEngine.SceneManagement.SceneManager.LoadScene(0); }, "ending-back"));
            return t;
        }

        public void ShowEnding() => StartCoroutine(EndingRoutine());

        IEnumerator EndingRoutine()
        {
            hud.style.display = DisplayStyle.None;
            // 장 끝 카드를 아직(최근 10초 안에) 안 보였으면 먼저 보인다
            if (Time.unscaledTime - chapterEndShownAt > 10f)
            {
                fader.style.opacity = 0;
                ShowChapterEnd();
                yield return new WaitForSecondsRealtime(4.0f);
            }
            ShowEndingPage();
        }

        void ShowEndingPage()
        {
            endingGlyphs.Clear();
            if (game != null)
            {
                var known = game.Data.Words.Keys.Where(w => game.State.Word(w).confirmed).ToList();
                foreach (var w in known)
                {
                    var c = UIKit.Box("ending-glyph");
                    c.Add(UIKit.Picture(PieceView.GlyphTexture(w), "ending-glyph-img"));
                    c.Add(UIKit.Text(ReadBoard.GuessOrBlank(w), "ending-glyph-guess", Face.Hand));
                    endingGlyphs.Add(c);
                }
                endingGlyphs.Add(UIKit.Text($"알아낸 글자 {known.Count} / {game.Data.Words.Count}", "ending-count", Face.Hand));
            }
            ending.style.display = DisplayStyle.Flex;
            UIKit.AnimateIn(ending, "ending-start", 60);
            StartCoroutine(FadeIn(1.2f));
        }

        // ── 페이드·장 제목 ────────────────────────────────
        public void FadeOut(float seconds) { if (seconds <= 0) fader.style.opacity = 1; else StartCoroutine(FadeOutRoutine(seconds)); }
        public IEnumerator FadeOutRoutine(float seconds) { yield return FadeTo(1f, seconds); }
        public IEnumerator FadeIn(float seconds) { yield return FadeTo(0f, seconds); }
        IEnumerator FadeTo(float to, float seconds)
        {
            float from = fader.resolvedStyle.opacity, t = 0;
            fader.pickingMode = PickingMode.Position;
            while (t < 1f) { t += Time.deltaTime / Mathf.Max(0.01f, seconds); fader.style.opacity = Mathf.Lerp(from, to, Mathf.SmoothStep(0, 1, t)); yield return null; }
            fader.pickingMode = to > 0.5f ? PickingMode.Position : PickingMode.Ignore;
        }

        /// <summary>
        /// 장 제목: 화면 전체에 장 그림(Resources/Pictures/chapter_card_n, n = small 속 숫자, 없으면 1)을 깔고 그 위에 글.
        /// small에 “끝”이 있으면 장 끝 그림(chapter_end_n)으로(= ShowChapterEnd). 약 4.2초, 그림·글이 따로 서서히.
        /// </summary>
        public void ShowChapterTitle(string small, string big)
        {
            if (big == "그리다 만 마을") big = "미완성 마을";   // 교수 요청: UI 문구는 “미완성”
            int n = ChapterNumber(small);
            bool end = !string.IsNullOrEmpty(small) && small.Contains("끝");
            ShowChapterCard(end ? "chapter_end_" + n : "chapter_card_" + n, small, big, end, 4.2f);
        }

        /// <summary>장 끝 카드(기본 chapter_end_1, “1장 끝” + 물고기 뱃속으로). ShowEnding이 끝 화면 앞에 먼저 보인다.</summary>
        public void ShowChapterEnd(string card = "chapter_end_1", string small = "1장 끝", string big = "물고기 뱃속으로")
            => ShowChapterCard(card, small, big, true, 4.6f);

        float chapterEndShownAt = -99f;

        static int ChapterNumber(string s)
        {
            if (string.IsNullOrEmpty(s)) return 1;
            foreach (var ch in s) if (ch >= '1' && ch <= '9') return ch - '0';
            return 1;
        }

        void ShowChapterCard(string card, string small, string big, bool end, float seconds)
        {
            if (end) chapterEndShownAt = Time.unscaledTime;
            chapterTitle.Clear();
            chapterTitle.EnableInClassList("chapter-end", end);
            var tex = Resources.Load<Texture2D>("Pictures/" + card);
            if (tex)
            {
                var img = new Image { image = tex, scaleMode = ScaleMode.ScaleAndCrop, pickingMode = PickingMode.Ignore };
                img.AddToClassList("chapter-card");
                chapterTitle.Add(img);
            }
            else chapterTitle.Add(UIKit.Box("chapter-card chapter-card-none"));
            var box = UIKit.Box("chapter-box"); chapterTitle.Add(box);
            box.Add(UIKit.Text(small ?? "", "chapter-small", Face.Serif));
            box.Add(UIKit.Text(big ?? "", "chapter-big", Face.SerifBold));
            box.Add(UIKit.Box("chapter-line"));
            StartCoroutine(CardRoutine(seconds));
        }

        IEnumerator CardRoutine(float seconds)
        {
            var el = chapterTitle;
            var box = el.Q(className: "chapter-box");
            el.style.display = DisplayStyle.Flex; el.style.opacity = 0;
            if (box != null) box.style.opacity = 0;
            el.AddToClassList("is-drawing");
            float t = 0; bool drawn = false;
            while (t < seconds)
            {
                t += Time.unscaledDeltaTime;
                el.style.opacity = Mathf.Clamp01(Mathf.Min(t / 0.9f, (seconds - t) / 0.9f));
                if (box != null) box.style.opacity = Mathf.Clamp01(Mathf.Min((t - 0.6f) / 0.8f, (seconds - 0.3f - t) / 0.6f));
                if (!drawn && t > 1.0f) { el.RemoveFromClassList("is-drawing"); drawn = true; }
                yield return null;
            }
            el.style.display = DisplayStyle.None;
        }

        IEnumerator ShowFor(VisualElement el, float seconds)
        {
            el.style.display = DisplayStyle.Flex; el.style.opacity = 0;
            el.AddToClassList("is-drawing");
            float t = 0;
            bool drawn = false;
            while (t < seconds)
            {
                t += Time.deltaTime;
                el.style.opacity = Mathf.Clamp01(Mathf.Min(t / 0.7f, (seconds - t) / 0.8f));
                if (!drawn && t > 0.25f) { el.RemoveFromClassList("is-drawing"); drawn = true; }
                yield return null;
            }
            el.style.display = DisplayStyle.None;
        }

        // ── 쪽 넘김(화-12: 구역 하나 = 그림책 한 쪽) ─────────
        /// <summary>
        /// 종이 한 장이 오른쪽에서 왼쪽으로 넘어가며 화면을 덮고(말린 가장자리·그림자), 다 덮였을 때 atMiddle()을 부른 뒤
        /// 계속 넘어가며 새 쪽을 드러내고, 위에 쪽 머리말(“— n —” + 구역 이름)을 잠깐 보인다. 약 0.9초.
        /// </summary>
        public IEnumerator PageTurn(Action atMiddle, string nextAreaName)
        {
            if (turning) { atMiddle?.Invoke(); yield break; }
            turning = true;
            float W = root.layout.width; if (float.IsNaN(W) || W <= 0) W = 1920f;
            const float curl = 160f;
            pageTurn.style.display = DisplayStyle.Flex;
            pageTurn.pickingMode = PickingMode.Position;   // 넘기는 동안 클릭 막기
            pageHeader.style.display = DisplayStyle.None;
            AudioHub.Play("page", 0.7f);
            float from = W + 10f, to = -curl;           // 시트 왼쪽(말린 가장자리) 위치: 화면 오른쪽 밖 → 화면 왼쪽 밖
            float t = 0f, dur = 0.4f;
            while (t < dur)
            {
                t += Time.unscaledDeltaTime;
                float k = Mathf.SmoothStep(0f, 1f, Mathf.Clamp01(t / dur));
                pageSheet.style.left = Mathf.Lerp(from, to, k);
                pageSheet.style.rotate = new UnityEngine.UIElements.Rotate(new Angle(Mathf.Sin(k * Mathf.PI) * -2.2f, AngleUnit.Degree));
                yield return null;
            }
            pageSheet.style.left = to;
            pageSheet.style.rotate = StyleKeyword.Null;
            try { atMiddle?.Invoke(); } catch (Exception e) { Debug.LogException(e); }
            yield return new WaitForSecondsRealtime(0.08f);
            // 드러내기: 같은 종이가 계속 왼쪽으로 넘어가며 빠진다
            float from2 = to, to2 = -W - curl * 2f;
            t = 0f;
            while (t < dur)
            {
                t += Time.unscaledDeltaTime;
                float k = Mathf.SmoothStep(0f, 1f, Mathf.Clamp01(t / dur));
                pageSheet.style.left = Mathf.Lerp(from2, to2, k);
                yield return null;
            }
            pageTurn.style.display = DisplayStyle.None;
            pageTurn.pickingMode = PickingMode.Ignore;
            turning = false;
            if (!string.IsNullOrEmpty(nextAreaName))
            {
                if (!pageNumbers.TryGetValue(nextAreaName, out var num)) { num = pageNumbers.Count + 2; pageNumbers[nextAreaName] = num; }
                pageNumber.text = $"— {num} —";
                pageName.text = nextAreaName;
                lastHeader = nextAreaName; lastHeaderAt = Time.unscaledTime;
                StartCoroutine(ShowFor(pageHeader, 2.6f));
            }
        }

        // ── HUD ─────────────────────────────────────────
        public void SetGoal(string text, string place, string hint = null)
        {
            goalHint.text = hint ?? "";
            goalHint.style.display = string.IsNullOrEmpty(hint) ? DisplayStyle.None : DisplayStyle.Flex;
            bool changed = goalText.text != (text ?? "");
            goalText.text = text ?? "";
            goalPlace.text = string.IsNullOrEmpty(place) ? "지금 할 일" : place;
            // 본 게임에는 목표 쪽지가 없다(안내는 세계 안에서). F2 개발용 겹쳐 보기에서만 보인다.
            goalCard.style.display = devGoal && !string.IsNullOrEmpty(text) ? DisplayStyle.Flex : DisplayStyle.None;
            if (devGoal && changed && !string.IsNullOrEmpty(text)) UIKit.AnimateIn(goalCard, "goal-new", 40);
        }

        // ── 연출용 ──────────────────────────────────────
        public void SetCinematic(bool on)
        {
            cinematic = on;
            letterbox.EnableInClassList("lb-on", on);
            if (Bound) { hud.EnableInClassList("hud-hidden", on); journalBtn.SetEnabled(!on); }
        }

        public void ShowNameplate(NpcActor n, string name) { StartCoroutine(NameplateRoutine(n, name)); }

        IEnumerator NameplateRoutine(NpcActor n, string name)
        {
            var box = UIKit.Box("nameplate");
            UIKit.Rotate(box, UIKit.Jitter(name, 2.5f));
            box.Add(UIKit.Text(name, "nameplate-text", Face.SerifBold));
            box.Add(UIKit.Box("nameplate-line"));
            box.Add(UIKit.Box("nameplate-pin"));
            worldLayer.Add(box);
            UIKit.AnimateIn(box, "is-drawing", 120);
            float t = 0;
            while (t < 4f && n)
            {
                t += Time.deltaTime;
                var cam = Camera.main;
                if (cam && root.panel != null)
                {
                    var sp = cam.WorldToScreenPoint(n.HeadPosition + Vector3.up * 0.55f);
                    var pp = RuntimePanelUtils.ScreenToPanel(root.panel, new Vector2(sp.x, Screen.height - sp.y));
                    float w = box.resolvedStyle.width;
                    box.style.left = pp.x - (float.IsNaN(w) ? 0 : w / 2f); box.style.top = pp.y - 86f;
                    box.style.opacity = Mathf.Clamp01(Mathf.Min(t / 0.5f, (4f - t) / 0.6f));
                }
                yield return null;
            }
            box.RemoveFromHierarchy();
        }

        public void SetFlashback(bool on) { flashback.style.display = on ? DisplayStyle.Flex : DisplayStyle.None; if (!on) flashback.Clear(); }

        public void ShowFlashbackLine(string sentenceId)
        {
            flashback.Clear();
            if (string.IsNullOrEmpty(sentenceId) || game == null || !game.Data.Sentences.ContainsKey(sentenceId)) return;
            var strip = UIKit.Box("flashback-strip");
            UIKit.Rotate(strip, UIKit.Jitter(sentenceId, 1.4f));
            strip.Add(new GlyphLine(sentenceId, 104f, allowTranslation: true));
            strip.Add(UIKit.Box("tape tape-top"));
            flashback.Add(strip);
            UIKit.AnimateIn(strip, "strip-start", 30);
            AudioHub.Play("page", 0.4f, 0.8f);
        }

        public void ShowBellyDark()
        {
            belly.style.display = DisplayStyle.Flex;
            belly.Clear();
            var blue = new VisualElement { name = "belly-blue" }; belly.Add(blue);
            var frag = new VisualElement { name = "belly-frag" }; belly.Add(frag);
            fader.style.opacity = 0;
        }

        public void Shake(float seconds) { if (!GameSettings.ScreenShake) return; if (Camera.main && Camera.main.TryGetComponent<FollowCamera>(out var fc)) fc.Shake(seconds); }

        public void SetPickPrompt(bool on)
        {
            pickPrompt.style.display = on ? DisplayStyle.Flex : DisplayStyle.None;
            if (on) UIKit.AnimateIn(pickPrompt, "strip-start", 30);
        }

        public void ShowHold(bool on) { holdBar.style.display = on ? DisplayStyle.Flex : DisplayStyle.None; SetHoldProgress(0); }
        public void SetHoldProgress(float k) { holdFill.style.width = Length.Percent(Mathf.Clamp01(k) * 100f); }

        public void OpenReadable(ReadableDef rd) { CloseAll(); readable.Open(rd); }

        string lastHeader; float lastHeaderAt = -99f;

        public void ShowPlaceName(string name)
        {
            if (string.IsNullOrEmpty(name)) return;
            if (name == lastHeader && Time.unscaledTime - lastHeaderAt < 4f) return;   // 방금 쪽 머리말로 보였으면 또 띄우지 않음
            placeLabel.text = name;
            StartCoroutine(ShowFor(placeBanner, 3.4f));
        }

        public void SetCursor(CursorKind kind, string label)
        {
            if (string.IsNullOrEmpty(label) && !string.IsNullOrEmpty(exitLabel)) label = exitLabel;   // 출구 위에서는 출구 이름 유지
            tooltip.style.display = string.IsNullOrEmpty(label) ? DisplayStyle.None : DisplayStyle.Flex;
            tooltipLabel.text = label ?? "";
            cursorKind = kind;
            ApplyCursor();
        }

        /// <summary>출구(다음 쪽으로 넘어가는 자리)에 마우스가 있을 때: 커서 옆 손글씨 이름 + 걷기 커서. null이면 지움(화-12).</summary>
        public void SetExitHover(string label)
        {
            exitLabel = string.IsNullOrEmpty(label) ? null : label;
            tooltip.EnableInClassList("tooltip-exit", exitLabel != null);
            tooltip.style.display = exitLabel != null ? DisplayStyle.Flex : DisplayStyle.None;
            tooltipLabel.text = exitLabel != null ? exitLabel + " →" : "";
            ApplyCursor();
        }

        void ApplyCursor()
        {
            // 기본은 보통 화살표(바닥 위도). 출구 위에서만 걷기 커서, 대상 위에서는 말·손.
            if (exitLabel != null && !PointerOverUI && !BlocksWorld) { CursorSet.Apply(CursorKind.Walk); return; }
            CursorSet.Apply(PointerOverUI ? CursorKind.Default : cursorKind == CursorKind.Walk ? CursorKind.Default : cursorKind);
        }

        /// <summary>알림 쪽지. confirmed=true이고 text가 글자 id면 화면 가운데 확정 도장으로 보인다(Core: WordConfirmed → Toast("글자 확정", 글자, true)).</summary>
        public void Toast(string head, string text, bool confirmed)
        {
            if (confirmed && !string.IsNullOrEmpty(text) && PieceView.GlyphTexture(text) != null)
            {
                stampQueue.Enqueue(text);
                if (!stamping) StartCoroutine(StampRoutine());
                return;
            }
            if (head == "길잡이" && !devGoal) return;   // 길잡이 알림은 본 게임에서 쓰지 않음(F2 개발용에서만)
            if (AnyScreenOpen) { pendingToasts.Enqueue((head, text)); return; }   // 창이 열린 동안은 모아 두었다가 닫히면
            var t = UIKit.Box("toast");
            UIKit.Rotate(t, UIKit.Jitter((head ?? "") + text + Time.frameCount, 1.2f));
            if (!string.IsNullOrEmpty(head)) t.Add(UIKit.Text(head, "toast-head", Face.Hand));
            t.Add(UIKit.Text(text ?? "", "toast-text", Face.Serif));
            toastLayer.Add(t);
            UIKit.AnimateIn(t, "toast-start", 30);
            StartCoroutine(Expire(t, 5f));
        }

        IEnumerator Expire(VisualElement el, float s)
        {
            yield return new WaitForSeconds(s);
            UIKit.AnimateOutAndRemove(el, "toast-out", 0.5f);
        }

        /// <summary>글자 확정 순간(재미 지점): 가운데 종이 위 큰 글자 → 붉은 도장이 찍히고 → 추측이 손글씨로 → 기록 공책으로 날아감.</summary>
        IEnumerator StampRoutine()
        {
            stamping = true;
            while (stampQueue.Count > 0)
            {
                var w = stampQueue.Dequeue();
                var card = UIKit.Box("stamp-card");
                UIKit.Rotate(card, UIKit.Jitter(w, 2.5f));
                card.Add(UIKit.Picture(PieceView.GlyphTexture(w), "stamp-glyph"));
                var seal = UIKit.Box("stamp-seal");
                card.Add(seal);
                var guess = game != null ? game.State.Word(w).guess : "";
                var gl = UIKit.Text(string.IsNullOrEmpty(guess) ? w : guess, "stamp-guess", Face.Hand);
                card.Add(gl);
                card.Add(UIKit.Text("뜻을 알아냈다", "stamp-caption", Face.Serif));
                stampLayer.Add(card);
                seal.AddToClassList("seal-start"); gl.AddToClassList("guess-start");
                UIKit.AnimateIn(card, "stamp-start", 20);
                yield return new WaitForSeconds(0.38f);
                seal.RemoveFromClassList("seal-start");
                yield return new WaitForSeconds(0.25f);
                gl.RemoveFromClassList("guess-start");
                yield return new WaitForSeconds(1.5f);
                card.AddToClassList("stamp-fly");
                yield return new WaitForSeconds(0.55f);
                card.RemoveFromHierarchy();
                UIKit.AnimateIn(journalBtn, "journal-pop", 20);
            }
            stamping = false;
        }

        // ── 창 ──────────────────────────────────────────
        public void OpenDialogue(DialogueDef d, Action<DialogueDef, bool> closed) { CloseAll(); dialogue.Open(d, closed); }
        public void OpenInscription(InscriptionDef ins) { CloseAll(); inscription.Open(ins); }
        public void ToggleJournal()
        {
            if (guessPopup.IsOpen || pause.IsOpen || settings.IsOpen || decree.IsOpen) return;
            if (journal.IsOpen) journal.Close();
            else if (!dialogue.IsOpen && !inscription.IsOpen && !readable.IsOpen && title.style.display != DisplayStyle.Flex) journal.Open();
        }

        public void Escape()
        {
            if (guessPopup.IsOpen) { guessPopup.Close(); return; }
            if (settings.IsOpen) { settings.Back(); return; }
            if (pause.IsOpen) { if (!pause.CancelAsk()) ClosePause(); return; }
            if (decree.IsOpen) { decree.Close(); return; }
            if (readable.IsOpen) { readable.Close(); return; }
            if (journal.IsOpen) { journal.Close(); return; }
            if (inscription.IsOpen) { inscription.Close(); return; }
            if (dialogue.IsOpen) { dialogue.Escape(); return; }
            if (ending.style.display == DisplayStyle.Flex) return;
            if (title.style.display == DisplayStyle.Flex) return;
            OpenPause();
        }

        // ── 잠시 멈춤 · 설정 ─────────────────────────────
        public bool Paused => pause.IsOpen;

        public void OpenPause()
        {
            if (pause.IsOpen || !Bound) return;
            savedTimeScale = Time.timeScale > 0f ? Time.timeScale : 1f;
            Time.timeScale = 0f;
            pause.Open();
        }

        public void ClosePause()
        {
            if (!pause.IsOpen) return;
            pause.Close();
            Time.timeScale = savedTimeScale;
        }

        /// <summary>설정 공책(제목 화면·잠시 멈춤에서). 닫으면 열었던 곳으로 돌아간다.</summary>
        public void OpenSettings(SettingsScreen.Tab tab)
        {
            bool fromPause = pause.IsOpen;
            if (fromPause) pause.style.display = DisplayStyle.None;
            settings.Open(tab, () => { if (fromPause) pause.Open(); });
        }

        void SaveIfSafe() { var g = Game.I; if (g != null && Bound && !g.Busy) g.Save(); }

        void OnSettingsChanged()
        {
            float b = GameSettings.Brightness;
            brightness.style.backgroundColor = b < 0 ? new Color(0.05f, 0.04f, 0.035f, Mathf.Clamp01(-b * 1.6f)) : new Color(1f, 0.99f, 0.96f, Mathf.Clamp01(b * 1.1f));
            float s = GameSettings.UiScale;
            var sc = new Scale(new Vector2(s, s));
            toastLayer.style.transformOrigin = new TransformOrigin(Length.Percent(100), Length.Percent(0), 0f); toastLayer.style.scale = sc;
            journalBtn.style.transformOrigin = new TransformOrigin(Length.Percent(100), Length.Percent(0), 0f); journalBtn.style.scale = sc;
            tooltip.style.transformOrigin = new TransformOrigin(Length.Percent(0), Length.Percent(0), 0f); tooltip.style.scale = sc;
            helpLine.style.transformOrigin = new TransformOrigin(Length.Percent(0), Length.Percent(100), 0f); helpLine.style.scale = sc;
            pageHeader.style.transformOrigin = new TransformOrigin(Length.Percent(50), Length.Percent(0), 0f); pageHeader.style.scale = sc;
            CursorSet.Refresh();
        }

        void CloseAll() { if (journal.IsOpen) journal.Close(); if (inscription.IsOpen) inscription.Close(); if (readable.IsOpen) readable.Close(); }

        public void EditGuess(string word, VisualElement anchor, Action changed) => guessPopup.Open(word, anchor, changed);

        // ── 왕의 띠 벗기기(4-2 장치3) ───────────────────────
        /// <summary>띠를 끝까지 벗겼나(마지막 ShowDecree 기준).</summary>
        public bool DecreePeeled => decree != null && decree.Peeled;
        public bool DecreeOpen => decree != null && decree.IsOpen;
        public void DevPeelDecree() => decree?.DevPeel();
        public void CloseDecree() => decree?.Close();

        /// <summary>
        /// 그림판에 붙은 왕의 띠를 가까이 본다. 들뜬 오른쪽 모서리를 누른 채 왼쪽으로 끌어 띠를 젖히면 밑의 사람 글이 드러난다
        /// (반 넘게 젖히고 놓으면 끝까지 벗겨짐, 아니면 도로 붙음). 창을 닫으면(덮기·바깥·Esc) 끝난다. 벗겼는지는 DecreePeeled.
        /// bandTex·humanTex = Resources 경로 또는 Pictures/ 아래 이름(예: "decree_band", "decree_human").
        /// </summary>
        public IEnumerator ShowDecree(string bandTex, string humanTex) => ShowDecree(bandTex, humanTex, DecreeSentence, null);

        /// <summary>띠의 크리처 글(띠 그림 밑에 늘 보이는 글자 줄, 그림이 없으면 띠 위에도). 기본 「우리 → 바치다 → 귀한손님」.</summary>
        public string DecreeSentence = "s_we_offer_guest";

        /// <param name="bandSentence">띠 그림이 아직 없을 때 띠 위에 대신 그릴 크리처 문장 id(예: s_we_offer_guest)</param>
        /// <param name="humanText">사람 글 그림이 아직 없을 때 대신 보일 손글씨 본문</param>
        public IEnumerator ShowDecree(string bandTex, string humanTex, string bandSentence, string humanText)
        {
            CloseAll();
            bool open = true;
            decree.GlyphClicked = (w, el) => EditGuess(w, el, decree.RefreshLine);
            decree.Open(bandTex, humanTex, string.IsNullOrEmpty(bandSentence) ? DecreeSentence : bandSentence, humanText, () => open = false);
            while (open && decree.IsOpen) yield return null;
        }

        // ── 가르치는 몸짓(1-3 등: 크리처가 나/너를 짚어 보임) ─────────
        /// <summary>
        /// 대화창 왼쪽 쪽에 몸짓 그림 쪽지를 붙인다: "self" = 제 가슴 짚기, "other" = 상대 가리키기, "both" = 둘 다. null·""이면 뗌.
        /// 대화창이 닫혀 있으면 다음에 열 때 붙고, 대화창이 닫히면 떨어진다.
        /// </summary>
        public void ShowGestureHint(string kind) => dialogue.SetGestureHint(kind);

        // ── 기록: 글자를 마지막으로 본 자리 그림 ────────────────
        /// <summary>글자 word를 마지막으로 본 장면(화면 잘라 낸 그림)을 기록 공책 그 글자 쪽에 붙인다. 게임을 끄면 사라진다(저장 안 함).</summary>
        public void RememberSighting(string word, Texture tex)
        {
            JournalScreen.RememberSighting(word, tex);
            if (journal.IsOpen) journal.Refresh();
        }

        public void MarkInscriptionRead(Interactable it, string id) { it.GetComponent<InscriptionMarker>()?.ShowTranslation(); }

        // ── 극 대사 한 줄(퍼즐 아닌 글자, 뜻-28 ②) ─────────
        public void ShowStageLine(string sentenceId, string stage)
        {
            stageLine.Clear();
            if (string.IsNullOrEmpty(sentenceId) || game == null || !game.Data.Sentences.ContainsKey(sentenceId)) { stageLine.style.display = DisplayStyle.None; return; }
            stageLine.style.display = DisplayStyle.Flex;
            var strip = UIKit.Box("stage-strip");
            UIKit.Rotate(strip, UIKit.Jitter(sentenceId, 1.2f));
            // 누가·어디서(예: “문 너머”) — 띠 왼쪽 위 손글씨 쪽지
            if (!string.IsNullOrEmpty(stage)) { var tag = UIKit.Box("stage-tag"); tag.Add(UIKit.Text(stage, "stage-tag-text", Face.Hand)); strip.Add(tag); }
            var line = new GlyphLine(sentenceId, 80f, allowTranslation: true, clickable: true);
            line.GlyphClicked = (w, el) => EditGuess(w, el, () => line.Refresh());
            strip.Add(line);
            stageLine.Add(strip);
            UIKit.AnimateIn(strip, "strip-start", 30);
        }

        /// <summary>퍼즐이 아닌 글 한 줄: 낱말을 다 확정했으면 번역 문장, 아니면 낱글자 한 줄 + 그 밑 내 추측(GlyphLine).</summary>
        public VisualElement NonPuzzleLine(string sentenceId, float glyphSize)
        {
            var line = new GlyphLine(sentenceId, glyphSize, allowTranslation: true, clickable: true);
            line.GlyphClicked = (w, el) => EditGuess(w, el, () => line.Refresh());
            line.AddToClassList("np-line");
            return line;
        }

        // ── 머리 위 말(화-11: 글자만 한 줄) ─────────────────
        public void SetPersistentOverhead(NpcActor n, string sentence)
        {
            if (n == null) return;
            if (string.IsNullOrEmpty(sentence)) persistentWanted.Remove(n); else persistentWanted[n] = sentence;
            if (overheads.TryGetValue(n, out var o))
            {
                if (!o.persistent && !o.removing) return;   // 임시 말이 떠 있는 동안은 두고, 끝나면 되살린다
                if (o.persistent && o.sentence == sentence && !o.removing) return;
            }
            if (string.IsNullOrEmpty(sentence)) { RemoveOverhead(n); return; }
            RemoveOverhead(n);
            AddOverhead(n, sentence, persistent: true, seconds: 0);
        }

        public void ShowOverhead(NpcActor n, string sentence, float seconds)
        {
            if (n == null) return;
            RemoveOverhead(n);
            AddOverhead(n, sentence, persistent: false, seconds: seconds * GameSettings.BalloonTime);   // 설정: 말풍선 표시 시간(여기서 곱함 — Core는 곱하지 않기)
            AudioHub.Play("speak", 0.35f, 1.15f);
        }

        void AddOverhead(NpcActor n, string sentence, bool persistent, float seconds)
        {
            if (game == null || string.IsNullOrEmpty(sentence) || !game.Data.Sentences.ContainsKey(sentence)) return;
            var o = new Overhead { sentence = sentence, persistent = persistent, until = persistent ? float.MaxValue : Time.time + seconds, range = persistent ? OverheadRange(n, sentence) : 16f };
            overheads[n] = o;   // 먼저 등록(문장 생성 중 상태가 바뀌어 다시 불려도 겹치지 않게)
            o.el = UIKit.Box("overhead");
            o.el.style.visibility = Visibility.Hidden;
            o.body = UIKit.Box("oh-body oh-hidden");
            o.el.Add(o.body);
            o.card = UIKit.Box("oh-card", PickingMode.Position);
            o.body.Add(o.card);
            o.line = new GlyphLine(sentence, 64f * GameSettings.UiScale, allowTranslation: true, clickable: true, place: PlaceZone.Current, markSeen: false);
            var line = o.line;
            line.GlyphClicked = (w, el) => { if (!cinematic) EditGuess(w, el, () => line.Refresh()); };
            o.card.Add(line);
            o.tail = UIKit.Box("oh-tail");
            o.body.Add(o.tail);
            worldLayer.Add(o.el);
        }

        /// <summary>chapter1.json overheads[]의 range(이 거리 안에서 보여야 낱말을 “봄”으로 침). 없으면 8m.</summary>
        float OverheadRange(NpcActor n, string sentence)
        {
            if (game == null || game.Data.Root == null) return 8f;
            foreach (var o in J.List(game.Data.Root, "overheads").OfType<Dictionary<string, object>>())
                if (J.Str(o, "npc") == n.npcId && J.Str(o, "sentence") == sentence && o.TryGetValue("range", out var r)) return Mathf.Max(1f, J.F(r));
            return 8f;
        }

        void RemoveOverhead(NpcActor n)
        {
            if (n == null || !overheads.TryGetValue(n, out var o)) return;
            overheads.Remove(n);
            if (o.el == null) return;
            if (o.el.resolvedStyle.visibility == Visibility.Hidden || o.el.style.display == DisplayStyle.None) { o.el.RemoveFromHierarchy(); return; }
            o.removing = true;
            o.body.AddToClassList("oh-hidden");
            o.el.pickingMode = PickingMode.Ignore; o.card.pickingMode = PickingMode.Ignore;
            o.el.schedule.Execute(() => o.el.RemoveFromHierarchy()).StartingIn(260);
        }

        // ── 말 걸기 표시 ─────────────────────────────────
        /// <summary>말을 걸 수 있는 크리처 머리 위 잉크 말풍선 표시를 강제로 켜거나 끈다(자동 판정보다 우선). ClearTalkMark로 자동으로 되돌림.</summary>
        public void SetTalkMark(NpcActor n, bool on) { if (n) talkOverride[n] = on; }
        public void ClearTalkMark(NpcActor n) { if (n) talkOverride.Remove(n); }

        /// <summary>Game.StateRefreshed마다: 열린 대화가 있는 크리처 = 말 걸기 표시.</summary>
        void RefreshTalkMarks()
        {
            if (game == null) return;
            talkAuto.Clear();
            foreach (var n in game.AllNpcs)
            {
                if (!n) continue;
                bool talkable = !game.Data.Npcs.TryGetValue(n.npcId ?? "", out var nd) || nd.Talkable;
                if (talkable && game.OpenDialogueFor(n.npcId) != null) talkAuto.Add(n);
            }
        }

        bool TalkMarkOn(NpcActor n) => talkOverride.TryGetValue(n, out var v) ? v : talkAuto.Contains(n);

        readonly Dictionary<InscriptionMarker, VisualElement> markerLabels = new Dictionary<InscriptionMarker, VisualElement>();

        void UpdateMarkers(Camera cam)
        {
            foreach (var m in InscriptionMarker.All)
            {
                if (!m.Translated) continue;
                if (!markerLabels.TryGetValue(m, out var l))
                {
                    var sid = !string.IsNullOrEmpty(m.sentenceId) ? m.sentenceId : (game != null && game.Data.Inscriptions.TryGetValue(m.inscriptionId, out var ins) ? ins.Sentence : null);
                    var tr = game != null ? game.Data.Translate(sid) : null;
                    l = UIKit.Box("world-translation");
                    l.Add(UIKit.Text(tr ?? "", "world-translation-text", Face.Hand));
                    worldLayer.Add(l);
                    markerLabels[m] = l;
                }
                var sp = cam.WorldToScreenPoint(m.LabelPosition);
                float dist = game && game.player ? Vector3.Distance(game.player.transform.position, m.transform.position) : 99f;
                bool show = sp.z > 0 && dist < 9f && !HidesWorldUI;
                l.style.display = show ? DisplayStyle.Flex : DisplayStyle.None;
                if (!show) continue;
                var pp = RuntimePanelUtils.ScreenToPanel(root.panel, new Vector2(sp.x, Screen.height - sp.y));
                float w = l.resolvedStyle.width;
                l.style.left = pp.x - (float.IsNaN(w) ? 0 : w / 2f); l.style.top = pp.y - 24f;
                l.style.opacity = Mathf.Clamp01((9f - dist) / 3f);
            }
        }

        void UpdateWorldUI()
        {
            var cam = Camera.main;
            if (cam == null || root.panel == null) return;
            UpdateMarkers(cam);
            float W = root.layout.width, H = root.layout.height;
            if (float.IsNaN(W) || W <= 0) { W = 1920; H = 1080; }
            const float margin = 16f;
            var tops = new Dictionary<NpcActor, Rect>();
            var placedNow = new List<(NpcActor n, Overhead o, Rect rect, bool flip, float alpha, float depth)>();
            foreach (var kv in overheads.ToList())
            {
                var n = kv.Key; var o = kv.Value;
                if (n == null) { o.el?.RemoveFromHierarchy(); overheads.Remove(n); continue; }
                if (!n.gameObject.activeInHierarchy || Time.time > o.until)
                {
                    RemoveOverhead(n);
                    // 임시 말이 끝나면 상시 말을 되살린다(QA P2-14)
                    if (!o.persistent && persistentWanted.TryGetValue(n, out var keep) && !string.IsNullOrEmpty(keep) && n.gameObject.activeInHierarchy)
                        AddOverhead(n, keep, persistent: true, seconds: 0);
                    continue;
                }
                var sp = cam.WorldToScreenPoint(n.HeadPosition);
                var pp = sp.z > 0 ? RuntimePanelUtils.ScreenToPanel(root.panel, new Vector2(sp.x, Screen.height - sp.y)) : Vector2.zero;
                // 말하는 크리처가 화면 밖(또는 카메라 뒤)이면 말풍선을 숨긴다 — 가장자리에 붙이지 않음
                bool onScreen = sp.z > 0 && pp.x > -10f && pp.x < W + 10f && pp.y > 30f && pp.y < H + 60f;
                bool visible = onScreen && !HidesWorldUI;
                float dist = game && game.player ? Vector3.Distance(game.player.transform.position, n.transform.position) : 0;
                float alpha = o.persistent && dist > 16f ? 0f : 1f;   // 흐리게 하지 않음: 보이면 또렷하게, 멀면 숨김
                o.el.style.display = visible && alpha > 0.02f ? DisplayStyle.Flex : DisplayStyle.None;
                if (!visible || alpha <= 0.02f) continue;
                if (dist <= o.range) o.line.MarkSeen();   // 실제로 보이는 거리에서만 “봄”
                o.line.Refresh();
                float cw = o.card.resolvedStyle.width, ch = o.card.resolvedStyle.height;
                if (float.IsNaN(cw) || cw <= 1f) continue;   // 아직 배치 전: 다음 프레임에(0,0에 잠깐 뜨지 않게)
                // 꼬리 끝(카드 왼쪽 35px, 카드 아래 17px)이 머리 위에 오도록. 오른쪽 끝에 닿으면 꼬리를 뒤집어 왼쪽으로 편다.
                const float tipX = 35f, tipY = 28f, gap = 6f;
                bool flip = pp.x - tipX + cw > W - margin;
                float left = flip ? pp.x - (cw - tipX) : pp.x - tipX;
                float top = pp.y - ch - tipY - gap;
                left = Mathf.Clamp(left, margin, Mathf.Max(margin, W - margin - cw));
                placedNow.Add((n, o, new Rect(left, top, cw, ch), flip, alpha, sp.z));
            }
            // 가까이 선 크리처끼리 말풍선이 겹치면: 카메라에 가까운 쪽을 그대로 두고 먼 쪽을 위로 올린다
            placedNow.Sort((x, y) => x.depth.CompareTo(y.depth));
            var taken = new List<Rect>();
            foreach (var it in placedNow)
            {
                var r = it.rect;
                for (int guard = 0; guard < 8; guard++)
                {
                    bool moved = false;
                    foreach (var t in taken)
                        if (r.Overlaps(new Rect(t.x - 6f, t.y - 6f, t.width + 12f, t.height + 12f)))
                        { r.y = t.y - r.height - 10f; moved = true; }
                    if (!moved) break;
                }
                taken.Add(r);
                var o = it.o;
                o.tail.EnableInClassList("oh-tail-flip", it.flip);
                o.tail.style.display = Mathf.Abs(r.y - it.rect.y) > 1f ? DisplayStyle.None : DisplayStyle.Flex;   // 올려 쌓인 말풍선은 꼬리 없이
                o.el.style.left = r.x; o.el.style.top = Mathf.Max(margin, r.y);
                o.el.style.opacity = it.alpha;
                o.card.pickingMode = cinematic || o.removing ? PickingMode.Ignore : PickingMode.Position;
                tops[it.n] = r;
                if (!o.placed)
                {
                    o.placed = true;
                    o.el.style.visibility = Visibility.Visible;
                    o.body.schedule.Execute(() => { if (!o.removing) o.body.RemoveFromClassList("oh-hidden"); }).StartingIn(16);
                }
            }
            UpdateTalkMarks(cam, tops, W, H);
            UpdateInteractMarkers(cam, W, H);
            UpdateThought(cam, W, H);
        }

        // ── 둘레 살피기(휠 클릭): 누를 수 있는 것마다 잉크 동그라미 + 아이콘 ─────────
        class Marker { public Vector3 world; public VisualElement el; public float until; public bool leaving; }
        readonly List<Marker> markers = new List<Marker>();

        /// <summary>휠 클릭 때 Core가 부름: 화면 안의 대상마다 잉크 동그라미와 작은 아이콘(말·손·눈·출구)과 이름을 seconds 동안 보인다. 화면 밖은 숨김.</summary>
        public void ShowInteractMarkers(List<(Vector3 world, CursorKind kind, string label)> items, float seconds)
        {
            foreach (var m in markers) m.el.RemoveFromHierarchy();
            markers.Clear();
            if (items == null) return;
            int i = 0;
            foreach (var it in items)
            {
                var el = UIKit.Box("imark-pos");   // 자리·글자 크기 배율
                el.style.scale = new Scale(new Vector2(GameSettings.UiScale, GameSettings.UiScale));
                var body = UIKit.Box("imark"); el.Add(body);   // 튀어나오는 움직임
                body.Add(UIKit.Box("imark-ring"));
                string icon = it.kind == CursorKind.Talk ? "imark-talk" : it.kind == CursorKind.Use ? "imark-touch" : it.kind == CursorKind.Walk ? "imark-exit" : "imark-eye";
                body.Add(UIKit.Box("imark-icon " + icon));
                if (!string.IsNullOrEmpty(it.label))
                {
                    var lab = UIKit.Box("imark-tag");
                    UIKit.Rotate(lab, UIKit.Jitter(it.label, 3f));
                    lab.Add(UIKit.Text(it.label, "imark-label", Face.Hand));
                    body.Add(lab);
                }
                el.style.visibility = Visibility.Hidden;
                worldLayer.Add(el);
                UIKit.AnimateIn(body, "imark-start", 30 + 45 * i++);
                markers.Add(new Marker { world = it.world, el = el, until = Time.unscaledTime + Mathf.Max(0.5f, seconds) });
            }
            AudioHub.Play("piece", 0.35f, 1.5f);
        }

        void UpdateInteractMarkers(Camera cam, float W, float H)
        {
            for (int i = markers.Count - 1; i >= 0; i--)
            {
                var m = markers[i];
                if (Time.unscaledTime > m.until && !m.leaving)
                {
                    m.leaving = true;
                    UIKit.AnimateOutAndRemove(m.el, "imark-out", 0.35f);
                    continue;
                }
                if (m.leaving) { if (m.el.parent == null) markers.RemoveAt(i); continue; }
                var sp = cam.WorldToScreenPoint(m.world);
                var pp = sp.z > 0 ? RuntimePanelUtils.ScreenToPanel(root.panel, new Vector2(sp.x, Screen.height - sp.y)) : Vector2.zero;
                bool show = sp.z > 0 && pp.x > 20f && pp.x < W - 20f && pp.y > 20f && pp.y < H - 20f && !HidesWorldUI;
                m.el.style.display = show ? DisplayStyle.Flex : DisplayStyle.None;
                if (!show) continue;
                m.el.style.left = pp.x - 45f; m.el.style.top = pp.y - 45f;
                m.el.style.visibility = Visibility.Visible;
            }
        }

        // ── 주인공 속생각(손글씨 생각 풍선) ─────────────────
        readonly Queue<(string text, float seconds)> thoughtQueue = new Queue<(string, float)>();
        VisualElement thoughtEl;
        float thoughtUntil;

        /// <summary>주인공의 짧은 속생각(한국어)을 머리 위 손글씨 생각 풍선(점점이 작아지는 동그라미 꼬리)으로 seconds 동안. 여럿이면 차례로.</summary>
        public void ShowThought(string text, float seconds = 3.5f)
        {
            if (string.IsNullOrEmpty(text)) return;
            thoughtQueue.Enqueue((text, seconds * GameSettings.BalloonTime));
        }

        void UpdateThought(Camera cam, float W, float H)
        {
            if (thoughtEl != null && Time.unscaledTime > thoughtUntil)
            {
                UIKit.AnimateOutAndRemove(thoughtEl, "thought-out", 0.3f);
                thoughtEl = null;
                thoughtUntil = Time.unscaledTime + 0.25f;
            }
            if (thoughtEl == null && thoughtQueue.Count > 0 && Time.unscaledTime >= thoughtUntil)
            {
                var (text, secs) = thoughtQueue.Dequeue();
                thoughtEl = UIKit.Box("thought");
                var card = UIKit.Box("thought-card");
                var tl = UIKit.Text(text, "thought-text", Face.Hand);
                tl.style.fontSize = 32f * GameSettings.UiScale;
                card.Add(tl);
                thoughtEl.Add(card);
                thoughtEl.Add(UIKit.Box("thought-dot thought-dot-1"));
                thoughtEl.Add(UIKit.Box("thought-dot thought-dot-2"));
                thoughtEl.Add(UIKit.Box("thought-dot thought-dot-3"));
                thoughtEl.style.visibility = Visibility.Hidden;
                worldLayer.Add(thoughtEl);
                UIKit.AnimateIn(thoughtEl, "thought-start", 30);
                thoughtUntil = Time.unscaledTime + Mathf.Max(1f, secs);
            }
            if (thoughtEl == null) return;
            var hero = game != null && game.player ? game.player.transform : null;
            if (hero == null) { thoughtEl.style.display = DisplayStyle.None; return; }
            var sp = cam.WorldToScreenPoint(hero.position + Vector3.up * 1.4f);
            bool show = sp.z > 0 && !HidesWorldUI;
            thoughtEl.style.display = show ? DisplayStyle.Flex : DisplayStyle.None;
            if (!show) return;
            var pp = RuntimePanelUtils.ScreenToPanel(root.panel, new Vector2(sp.x, Screen.height - sp.y));
            float w = thoughtEl.resolvedStyle.width, h = thoughtEl.resolvedStyle.height;
            if (float.IsNaN(w) || w < 1f) return;
            // 꼬리 동그라미 끝(왼쪽 아래)이 머리 위에 오도록, 풍선은 오른쪽 위로
            float left = Mathf.Clamp(pp.x - 18f, 16f, W - w - 16f);
            float top = Mathf.Clamp(pp.y - h, 16f, H - h - 16f);
            thoughtEl.style.left = left; thoughtEl.style.top = top;
            thoughtEl.style.visibility = Visibility.Visible;
        }

        void UpdateTalkMarks(Camera cam, Dictionary<NpcActor, Rect> tops, float W, float H)
        {
            var all = new HashSet<NpcActor>(talkAuto);
            foreach (var kv in talkOverride) if (kv.Value) all.Add(kv.Key);
            foreach (var n in talkMarks.Keys.ToList())
                if (n == null || !all.Contains(n)) { talkMarks[n].RemoveFromHierarchy(); talkMarks.Remove(n); }
            foreach (var n in all)
            {
                if (n == null) continue;
                if (!TalkMarkOn(n)) { if (talkMarks.TryGetValue(n, out var old)) { old.RemoveFromHierarchy(); talkMarks.Remove(n); } continue; }
                if (!talkMarks.TryGetValue(n, out var m))
                {
                    m = UIKit.Box("talk-mark");
                    worldLayer.Add(m);
                    talkMarks[n] = m;
                    UIKit.AnimateIn(m, "talk-start", 30);
                }
                var sp = cam.WorldToScreenPoint(n.HeadPosition + Vector3.up * 0.45f);
                float dist = game && game.player ? Vector3.Distance(game.player.transform.position, n.transform.position) : 0;
                var mp = sp.z > 0 ? RuntimePanelUtils.ScreenToPanel(root.panel, new Vector2(sp.x, Screen.height - sp.y)) : Vector2.zero;
                bool onScreen = sp.z > 0 && mp.x > 0f && mp.x < W && mp.y > 40f && mp.y < H;
                bool show = n.gameObject.activeInHierarchy && onScreen && !HidesWorldUI && !cinematic && (game == null || !game.Busy) && dist < 22f;
                m.style.display = show ? DisplayStyle.Flex : DisplayStyle.None;
                if (!show) continue;
                float bob = Mathf.Sin(Time.time * 2.6f + n.GetInstanceID()) * 4f;
                if (tops.TryGetValue(n, out var r))
                {
                    m.style.left = r.xMax - 26f; m.style.top = r.yMin - 34f + bob;
                }
                else
                {
                    m.style.left = mp.x - 26f; m.style.top = mp.y - 60f + bob;
                }
                m.style.opacity = Mathf.Clamp01((22f - dist) / 6f);
            }
        }
    }
}
