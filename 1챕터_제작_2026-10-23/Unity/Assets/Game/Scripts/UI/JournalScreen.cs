using System.Collections.Generic;
using System.Linq;
using OUAT.Core;
using UnityEngine;
using UnityEngine.UIElements;

namespace OUAT.UI
{
    /// <summary>
    /// 기록 공책(뜻-13, 화-07). 왼쪽 쪽: 이 장의 글자 17칸(못 본 글자 = 빈 연필 칸, 본 글자 = 글자 + 연필 추측, 확정 = 붉은 도장)
    /// 또는 「문장」 장(읽어 낸 새김 번역). 오른쪽 쪽: 고른 글자 — 큰 글자, 추측(직접 쓰기), 메모, 처음 본 곳, 이 글자가 나온 말.
    /// </summary>
    public class JournalScreen : VisualElement
    {
        readonly UIRoot ui;
        readonly VisualElement spread, grid, sentenceList, wordsPage, sentencesPage, tabWords, tabSentences, detail, detailEmpty, dSeal, dLines, dGlyphWrap;
        readonly Label count, dStatus, dSeen;
        readonly Image dGlyph;
        readonly TextField dGuess, dMemo;
        readonly ScrollView sentenceScroll, lineScroll;
        string selected;
        bool sentencesTab;
        readonly VisualElement dSight, dSightEmpty;
        readonly Image dSightImg;
        static readonly Dictionary<string, Texture> sightings = new Dictionary<string, Texture>();

        /// <summary>글자를 마지막으로 본 장면(화면 잘라 낸 그림). 같은 글자는 새 그림으로 바뀐다. 저장하지 않음.</summary>
        public static void RememberSighting(string word, Texture tex)
        {
            if (string.IsNullOrEmpty(word)) return;
            if (tex == null) sightings.Remove(word); else sightings[word] = tex;
        }

        public static Texture SightingOf(string word) => word != null && sightings.TryGetValue(word, out var t) && t != null ? t : null;
        bool editing;

        public bool IsOpen => style.display == DisplayStyle.Flex;

        public JournalScreen(UIRoot ui)
        {
            this.ui = ui;
            AddToClassList("screen"); AddToClassList("journal-screen");
            pickingMode = PickingMode.Position;
            style.display = DisplayStyle.None;
            RegisterCallback<PointerDownEvent>(e => { if (e.target == this) Close(); });
            Add(UIKit.Box("vignette"));
            spread = UIKit.Box("jr-spread", PickingMode.Position);
            Add(spread);

            // ── 왼쪽 쪽 ──
            var left = UIKit.Box("jr-left"); spread.Add(left);
            var head = UIKit.Box("jr-head"); left.Add(head);
            head.Add(UIKit.Text("기록", "jr-title", Face.SerifBold));
            count = UIKit.Text("", "jr-count", Face.Hand); head.Add(count);
            left.Add(UIKit.Box("jr-title-line"));

            wordsPage = UIKit.Box("jr-words"); left.Add(wordsPage);
            grid = UIKit.Box("jr-grid"); wordsPage.Add(grid);
            sentencesPage = UIKit.Box("jr-sentences"); left.Add(sentencesPage);
            sentenceScroll = new ScrollView(ScrollViewMode.Vertical) { verticalScrollerVisibility = ScrollerVisibility.Hidden, horizontalScrollerVisibility = ScrollerVisibility.Hidden };
            sentenceScroll.AddToClassList("jr-scroll");
            sentencesPage.Add(sentenceScroll);
            sentenceList = UIKit.Box("jr-sentence-list"); sentenceScroll.Add(sentenceList);

            // 공책 위로 삐져나온 꼬리표(장 넘기기)
            tabWords = Tab("글자", () => SetTab(false)); UIKit.Rotate(tabWords, -3f);
            tabSentences = Tab("문장", () => SetTab(true)); UIKit.Rotate(tabSentences, 2f);
            var tabs = UIKit.Box("jr-tabs"); tabs.Add(tabWords); tabs.Add(tabSentences); spread.Add(tabs);

            // ── 오른쪽 쪽: 고른 글자 ──
            var right = UIKit.Box("jr-right"); spread.Add(right);
            detailEmpty = UIKit.Text("글자를 고르면 여기에 적는다", "jr-empty", Face.Hand); right.Add(detailEmpty);
            detail = UIKit.Box("jr-detail"); right.Add(detail);
            var top = UIKit.Box("jr-detail-top"); detail.Add(top);
            dGlyphWrap = UIKit.Box("jr-glyph-wrap"); top.Add(dGlyphWrap);
            dGlyph = UIKit.Picture(null, "jr-glyph"); dGlyphWrap.Add(dGlyph);
            dSeal = UIKit.Box("jr-seal"); dGlyphWrap.Add(dSeal);
            var fields = UIKit.Box("jr-fields"); top.Add(fields);
            fields.Add(UIKit.Text("뜻", "field-label", Face.Serif));
            dGuess = new TextField { maxLength = 20 }; dGuess.AddToClassList("guess-field"); dGuess.AddToClassList("jr-guess"); UIKit.SetFace(dGuess, Face.Hand);
            fields.Add(dGuess);
            fields.Add(UIKit.Box("field-line"));
            dStatus = UIKit.Text("", "jr-status", Face.Hand); fields.Add(dStatus);
            dSeen = UIKit.Text("", "jr-seen", Face.Serif); fields.Add(dSeen);
            // 가운데 줄: 마지막으로 본 자리(그림 칸) + 메모
            var mid = UIKit.Box("jr-mid"); detail.Add(mid);
            var sightCol = UIKit.Box("jr-sight-col"); mid.Add(sightCol);
            sightCol.Add(UIKit.Text("마지막으로 본 자리", "field-label", Face.Serif));
            dSight = UIKit.Box("jr-sight"); sightCol.Add(dSight);
            UIKit.Rotate(dSight, -1.6f);
            dSightImg = new Image { scaleMode = ScaleMode.ScaleAndCrop, pickingMode = PickingMode.Ignore };
            dSightImg.AddToClassList("jr-sight-img"); dSight.Add(dSightImg);
            dSight.Add(UIKit.Box("tape jr-sight-tape"));
            dSightEmpty = UIKit.Box("jr-sight-empty"); dSight.Add(dSightEmpty);
            dSightEmpty.Add(UIKit.Text("아직 그려 두지 못했다", "jr-sight-empty-text", Face.Hand));
            var memoCol = UIKit.Box("jr-memo-col"); mid.Add(memoCol);
            memoCol.Add(UIKit.Text("메모", "field-label", Face.Serif));
            dMemo = new TextField { multiline = true, maxLength = 300 }; dMemo.AddToClassList("memo-field"); dMemo.AddToClassList("jr-memo"); UIKit.SetFace(dMemo, Face.Hand);
            memoCol.Add(dMemo);
            detail.Add(UIKit.Text("이 글자가 나온 말", "field-label jr-lines-label", Face.Serif));
            lineScroll = new ScrollView(ScrollViewMode.Vertical) { verticalScrollerVisibility = ScrollerVisibility.Hidden, horizontalScrollerVisibility = ScrollerVisibility.Hidden };
            lineScroll.AddToClassList("jr-lines-scroll");
            detail.Add(lineScroll);
            dLines = UIKit.Box("jr-lines"); lineScroll.Add(dLines);

            dGuess.RegisterCallback<KeyDownEvent>(e => { if (e.keyCode == KeyCode.Return || e.keyCode == KeyCode.KeypadEnter) { CommitGuess(); e.StopPropagation(); } }, TrickleDown.TrickleDown);
            dGuess.RegisterCallback<FocusInEvent>(_ => editing = true);
            dGuess.RegisterCallback<FocusOutEvent>(_ => { CommitGuess(); editing = false; });
            dMemo.RegisterCallback<FocusInEvent>(_ => editing = true);
            dMemo.RegisterCallback<FocusOutEvent>(_ => { CommitMemo(); editing = false; });

            var close = UIKit.OnClick(UIKit.Box("close-x jr-close"), Close);
            spread.Add(close);
        }

        static VisualElement Tab(string text, System.Action a)
        {
            var t = UIKit.OnClick(UIKit.Box("jr-tab"), a);
            t.Add(UIKit.Text(text, "jr-tab-text", Face.Hand));
            return t;
        }

        void SetTab(bool sentences)
        {
            sentencesTab = sentences;
            AudioHub.Play("page", 0.35f, 1.2f);
            Refresh();
        }

        public void Open()
        {
            var g = Game.I;
            if (g == null) return;
            if (selected == null || !g.State.Word(selected).seen)
                selected = ui.NewWords.FirstOrDefault() ?? g.State.SeenWords.Select(w => w.id).FirstOrDefault();
            style.display = DisplayStyle.Flex;
            Refresh();
            UIKit.AnimateIn(spread, "jr-start", 20);
            AudioHub.Play("page", 0.5f);
        }

        public void Close()
        {
            if (!IsOpen) return;
            CommitGuess(); CommitMemo();
            dGuess.Blur(); dMemo.Blur();
            style.display = DisplayStyle.None;
            ui.ClearNewWords();
        }

        void CommitGuess()
        {
            var g = Game.I;
            if (g == null || selected == null) return;
            var st = g.State.Word(selected);
            if ((dGuess.value ?? "").Trim() == (st.guess ?? "")) return;
            AudioHub.Play("quill", 0.5f);
            g.State.SetGuess(selected, dGuess.value, g.Data.IsGuessCorrect);
        }

        void CommitMemo()
        {
            var g = Game.I;
            if (g == null || selected == null) return;
            if ((dMemo.value ?? "") == (g.State.Word(selected).memo ?? "")) return;
            g.State.SetMemo(selected, dMemo.value);
        }

        public void Refresh()
        {
            var g = Game.I;
            if (g == null) return;
            var all = g.Data.Words.Keys.ToList();
            int seen = all.Count(w => g.State.Word(w).seen);
            int confirmed = all.Count(w => g.State.Word(w).confirmed);
            count.text = $"알아낸 글자 {confirmed} · 본 글자 {seen} · 이 장 {all.Count}";
            tabWords.EnableInClassList("jr-tab-on", !sentencesTab);
            tabSentences.EnableInClassList("jr-tab-on", sentencesTab);
            wordsPage.style.display = sentencesTab ? DisplayStyle.None : DisplayStyle.Flex;
            sentencesPage.style.display = sentencesTab ? DisplayStyle.Flex : DisplayStyle.None;
            if (sentencesTab) BuildSentences(g); else BuildGrid(g, all);
            RefreshDetail(g);
        }

        void BuildGrid(Game g, List<string> all)
        {
            grid.Clear();
            int i = 0;
            foreach (var w in all)
            {
                var st = g.State.Word(w);
                var slot = UIKit.Box("jr-slot", st.seen ? PickingMode.Position : PickingMode.Ignore);
                slot.style.translate = new Translate(UIKit.Jitter(w + "x", 5f), UIKit.Jitter(w + "y", 6f));
                UIKit.Rotate(slot, UIKit.Jitter(w, 2.2f));
                if (!st.seen)
                {
                    slot.AddToClassList("jr-slot-blank");
                    slot.Add(UIKit.Box("jr-blank"));
                    slot.Add(UIKit.Text((i + 1).ToString(), "jr-slot-num", Face.Hand));
                }
                else
                {
                    if (w == selected) slot.Add(UIKit.Box("jr-ring"));
                    slot.Add(UIKit.Picture(PieceView.GlyphTexture(w), "jr-slot-glyph"));
                    var gl = UIKit.Text(st.confirmed ? ReadBoard.GuessOrBlank(w) : string.IsNullOrEmpty(st.guess) ? "?" : st.guess, "jr-slot-guess", Face.Hand);
                    gl.EnableInClassList("jr-slot-guess-ok", st.confirmed);
                    gl.EnableInClassList("jr-slot-guess-none", !st.confirmed && string.IsNullOrEmpty(st.guess));
                    slot.Add(gl);
                    if (st.confirmed) slot.Add(UIKit.Box("jr-slot-seal"));
                    if (!string.IsNullOrEmpty(st.memo)) slot.Add(UIKit.Box("jr-slot-memo"));
                    if (ui.NewWords.Contains(w)) slot.Add(UIKit.Text("새", "jr-slot-new", Face.Hand));
                    var id = w;
                    UIKit.OnClick(slot, () => Select(id));
                }
                grid.Add(slot);
                i++;
            }
        }

        void BuildSentences(Game g)
        {
            sentenceList.Clear();
            var read = g.Data.Inscriptions.Values.Where(x => !x.IsDisplay && g.State.InscriptionRead(x.Id)).ToList();
            if (read.Count == 0)
            {
                sentenceList.Add(UIKit.Text("아직 읽어 낸 새김이 없다.\n새김 앞에서 글자마다 뜻을 적고 「읽어 보기」.", "jr-empty-left", Face.Hand));
                return;
            }
            foreach (var ins in read)
            {
                var block = UIKit.Box("jr-sentence");
                var place = g.Data.Places.TryGetValue(ins.Place ?? "", out var p) ? p.Name : "";
                block.Add(UIKit.Text(string.IsNullOrEmpty(place) ? ins.Label : $"{ins.Label} · {place}", "jr-sentence-head", Face.Serif));
                foreach (var line in ins.Lines)
                {
                    var tr = g.Data.Translate(line);
                    block.Add(UIKit.Text(string.IsNullOrEmpty(tr) ? "(읽어 냈다)" : tr, "jr-sentence-text", Face.Serif));
                    var gl = new GlyphLine(line, 40f, allowTranslation: false, clickable: true, markSeen: false);
                    gl.GlyphClicked = (w, el) => Select(w);
                    gl.AddToClassList("jr-sentence-glyphs");
                    block.Add(gl);
                }
                sentenceList.Add(block);
            }
        }

        void Select(string w)
        {
            CommitGuess(); CommitMemo();
            dGuess.Blur(); dMemo.Blur(); editing = false;
            selected = w;
            AudioHub.Play("piece", 0.25f, 1.4f);
            Refresh();
            UIKit.AnimateIn(detail, "detail-start", 20);
        }

        void RefreshDetail(Game g)
        {
            bool has = selected != null && g.State.Word(selected).seen;
            detail.style.display = has ? DisplayStyle.Flex : DisplayStyle.None;
            detailEmpty.style.display = has ? DisplayStyle.None : DisplayStyle.Flex;
            if (!has) return;
            var st = g.State.Word(selected);
            dGlyph.image = PieceView.GlyphTexture(selected);
            dSeal.style.display = st.confirmed ? DisplayStyle.Flex : DisplayStyle.None;
            var sight = SightingOf(selected);
            dSightImg.image = sight;
            dSightImg.style.display = sight != null ? DisplayStyle.Flex : DisplayStyle.None;
            dSightEmpty.style.display = sight != null ? DisplayStyle.None : DisplayStyle.Flex;
            dSight.EnableInClassList("jr-sight-has", sight != null);
            if (!editing)
            {
                dGuess.SetValueWithoutNotify(st.guess ?? "");
                dMemo.SetValueWithoutNotify(st.memo ?? "");
            }
            dStatus.text = st.confirmed ? (st.readConfirmed ? "새김을 읽어 알아냈다" : "써서 통해 알아냈다")
                         : st.usedOk ? "써서 통한 적 있음 — 뜻이 맞으면 확정" : "아직 짐작뿐";
            dStatus.EnableInClassList("jr-status-ok", st.confirmed);
            dSeen.text = !string.IsNullOrEmpty(st.seenAt) && g.Data.Places.TryGetValue(st.seenAt, out var p) ? $"처음 본 곳 · {p.Name}" : "";

            dLines.Clear();
            var lines = g.Data.Sentences.Where(kv => UIRoot.SentenceSeen(g.State, kv.Key) && ChapterData.WordsOf(kv.Value).Contains(selected)).Select(kv => kv.Key).Take(6).ToList();
            foreach (var ins in g.Data.Inscriptions.Values.Where(x => !x.IsDisplay && g.State.InscriptionRead(x.Id)))
                foreach (var l in ins.Lines)
                    if (!lines.Contains(l) && g.Data.Sentences.TryGetValue(l ?? "", out var sp) && ChapterData.WordsOf(sp).Contains(selected) && lines.Count < 6) lines.Add(l);
            if (lines.Count == 0) dLines.Add(UIKit.Text("아직 문장 속에서 본 적 없다", "jr-lines-empty", Face.Hand));
            foreach (var sid in lines)
            {
                var row = UIKit.Box("jr-line");
                var gl = new GlyphLine(sid, 46f, allowTranslation: true, clickable: true, markSeen: false);
                gl.GlyphClicked = (w, el) => { if (w != selected) Select(w); };
                row.Add(gl);
                dLines.Add(row);
            }
        }
    }
}
