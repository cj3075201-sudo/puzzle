using System.Collections.Generic;
using System.Linq;
using OUAT.Core;
using UnityEngine;
using UnityEngine.UIElements;

namespace OUAT.UI
{
    /// <summary>
    /// 새겨진 풀이 문장(carved, 뜻-24): 돌판 위에 이미 조립된 판이 줄마다 놓이고, 글자 밑에 추측을 적는다(조립 없음).
    /// 「읽어 보기 n/m」: 모든 줄의 추측이 맞으면 함께 확정 + 번역 쪽지가 돌판에 붙음, 4글자 이상에서 하나만 틀리면 “거의 맞음”(뜻-27).
    /// 그림판(display)은 퍼즐이 아닌 글(뜻-28 ②): 그림책 낱장 — 큰 그림 + 그 아래 낱글자 줄(직소 없음, 다 알면 문장).
    /// </summary>
    public class InscriptionScreen : VisualElement
    {
        readonly UIRoot ui;
        readonly VisualElement stone, stoneBoards, stoneResult, page, pageLines, pageBand;
        readonly Label stoneLabel, pageLabel, pageNote;
        readonly Image picture, stonePicture;
        readonly VisualElement readBtn;
        readonly Label readLabel;
        InscriptionDef def;
        readonly List<ReadBoard> boards = new List<ReadBoard>();
        readonly List<GlyphLine> lines = new List<GlyphLine>();

        public bool IsOpen => style.display == DisplayStyle.Flex;

        public InscriptionScreen(UIRoot ui)
        {
            this.ui = ui;
            AddToClassList("screen"); AddToClassList("inscription-screen");
            pickingMode = PickingMode.Position;
            style.display = DisplayStyle.None;
            RegisterCallback<PointerDownEvent>(e => { if (e.target == this) Close(); });
            Add(UIKit.Box("vignette"));

            // ── 돌판(새김) ──
            stone = UIKit.Box("stone", PickingMode.Position); Add(stone);
            stoneLabel = UIKit.Text("", "stone-label", Face.Serif); stone.Add(stoneLabel);
            // 새김에 그림판 그림이 있으면(inscriptions[].image) 글자 판 위에 그림
            stonePicture = UIKit.Picture(null, "stone-picture"); stone.Add(stonePicture);
            stonePicture.style.width = 560; stonePicture.style.height = 300; stonePicture.style.flexShrink = 0; stonePicture.style.marginBottom = 6;
            stoneBoards = UIKit.Box("stone-boards"); stone.Add(stoneBoards);
            stone.Add(UIKit.OnClick(UIKit.Box("close-x stone-close"), Close));
            readBtn = UIKit.BrushButton("읽어 보기", TryRead, red: false, extra: "read-btn");
            readLabel = readBtn.Q<Label>(className: "brush-btn-label");
            stone.Add(readBtn);
            stoneResult = UIKit.Box("stone-result"); Add(stoneResult);

            // ── 그림책 낱장(그림판) ──
            page = UIKit.Box("picture-page", PickingMode.Position); Add(page);
            UIKit.Rotate(page, -0.7f);
            pageLabel = UIKit.Text("", "page-label", Face.Serif); page.Add(pageLabel);
            picture = UIKit.Picture(null, "page-picture"); page.Add(picture);
            pageNote = UIKit.Text("", "page-note", Face.Hand); page.Add(pageNote);
            // 그림 밑에 붙은 글자 띠(세계 종이 + 숯 선) — 그림이 크고 글자가 또렷하게
            pageBand = UIKit.Box("page-band"); page.Add(pageBand);
            UIKit.Rotate(pageBand, 0.5f);
            pageLines = UIKit.Box("page-lines"); pageBand.Add(pageLines);
            page.Add(UIKit.OnClick(UIKit.Box("close-x page-close"), Close));
        }

        public void Open(InscriptionDef ins)
        {
            def = ins;
            var g = Game.I;
            boards.Clear(); lines.Clear();
            stoneBoards.Clear(); stoneResult.Clear(); pageLines.Clear();
            bool display = ins.IsDisplay;
            stone.style.display = display ? DisplayStyle.None : DisplayStyle.Flex;
            stoneResult.style.display = display ? DisplayStyle.None : DisplayStyle.Flex;
            page.style.display = display ? DisplayStyle.Flex : DisplayStyle.None;

            if (display)
            {
                pageLabel.text = ins.Label;
                var tex = Resources.Load<Texture2D>("Pictures/" + J.Str(ins.Raw, "image", ins.Id)) ?? Resources.Load<Texture2D>("Pictures/" + ins.Id);
                picture.image = tex;
                picture.style.display = tex ? DisplayStyle.Flex : DisplayStyle.None;
                pageNote.text = tex || string.IsNullOrEmpty(ins.Picture) ? "" : ins.Picture;
                pageNote.style.display = string.IsNullOrEmpty(pageNote.text) ? DisplayStyle.None : DisplayStyle.Flex;
                foreach (var line in ins.Lines)
                {
                    if (!g.Data.Sentences.ContainsKey(line ?? "")) continue;
                    var gl = new GlyphLine(line, ins.Lines.Count > 1 ? 80f : 96f, allowTranslation: true, clickable: true, place: ins.Place);
                    gl.GlyphClicked = (w, el) => ui.EditGuess(w, el, RefreshAll);
                    gl.AddToClassList("page-line");
                    lines.Add(gl); pageLines.Add(gl);
                }
                pageBand.style.display = lines.Count > 0 ? DisplayStyle.Flex : DisplayStyle.None;
                UIKit.AnimateIn(page, "page-start", 20);
            }
            else
            {
                stoneLabel.text = ins.Label;
                // 짧은 한 줄은 크게(약 130px), 줄이 많을수록 작게 — 돌판 가운데를 채운다
                int n = ins.Lines.Count(l => g.Data.Sentences.ContainsKey(l ?? ""));
                float cell = n <= 1 ? 132f : n == 2 ? 104f : 84f;
                var image = J.Str(ins.Raw, "image", null);
                var stoneTex = string.IsNullOrEmpty(image) ? null : Resources.Load<Texture2D>("Pictures/" + image);
                stonePicture.image = stoneTex;
                stonePicture.style.display = stoneTex ? DisplayStyle.Flex : DisplayStyle.None;
                if (stoneTex) cell *= n <= 1 ? 0.8f : 0.7f;   // 그림 밑으로 글자 줄이 들어가게
                foreach (var line in ins.Lines)
                {
                    if (!g.Data.Sentences.TryGetValue(line ?? "", out var spec)) continue;
                    var b = new ReadBoard(spec, cell) { GlyphClicked = (w, el) => ui.EditGuess(w, el, RefreshAll) };
                    b.AddToClassList("stone-board");
                    boards.Add(b); stoneBoards.Add(b);
                    UIRoot.NoteSeen(line, ChapterData.WordsOf(spec), ins.Place);
                }
                bool read = g.State.InscriptionRead(ins.Id);
                readBtn.style.display = read || !ins.Confirms ? DisplayStyle.None : DisplayStyle.Flex;
                UpdateReadButton();
                if (read) ShowTranslation(false);
                UIKit.AnimateIn(stone, "stone-start", 20);
            }
            style.display = DisplayStyle.Flex;
            AudioHub.Play("page", 0.5f, 0.8f);
        }

        List<string> Words => boards.SelectMany(b => b.Pieces).Where(p => p.Word != null).Select(p => p.Word).Distinct().ToList();

        void UpdateReadButton()
        {
            var g = Game.I;
            if (g == null || def == null || def.IsDisplay) return;
            var words = Words;
            int filled = words.Count(w => !string.IsNullOrEmpty(g.State.Word(w).guess));
            readLabel.text = $"읽어 보기  {filled}/{words.Count}";
            readBtn.EnableInClassList("read-empty", filled == 0);
        }

        void RefreshAll()
        {
            foreach (var b in boards) b.RefreshGuesses();
            foreach (var l in lines) l.Refresh();
            UpdateReadButton();
        }

        void TryRead()
        {
            var g = Game.I;
            var words = Words;   // 낱말 단위(같은 글자가 두 번 나와도 하나, QA P2-16)
            if (words.All(w => string.IsNullOrEmpty(g.State.Word(w).guess)))
            {
                stoneResult.Clear();
                var hint = UIKit.Box("result-note");
                hint.Add(UIKit.Text("글자를 눌러 뜻부터 적어 보자", "result-text", Face.Hand));
                stoneResult.Add(hint);
                UIKit.AnimateIn(hint, "note-start", 30);
                UIKit.Shake(stoneBoards, 6f);
                return;
            }
            int wrong = words.Count(w => !g.Data.IsGuessCorrect(w, g.State.Word(w).guess));
            stoneResult.Clear();
            if (wrong == 0)
            {
                g.State.ConfirmByReading(words, def.Id);
                ShowTranslation(true);
                readBtn.style.display = DisplayStyle.None;
                g.Fire("read:" + def.Id);
                g.Save();
                AudioHub.Play("confirm", 0.6f);
            }
            else if (wrong == 1 && words.Count >= GameTuning.Get().almostMinGlyphs)
            {
                var note = UIKit.Box("result-note result-almost");
                note.Add(UIKit.Box("almost-mark"));
                note.Add(UIKit.Text("거의 — 하나가 다르다", "result-text", Face.Hand));
                stoneResult.Add(note);
                UIKit.AnimateIn(note, "note-start", 30);
                UIKit.Shake(stone, 5f);
                AudioHub.Play("almost", 0.6f);
            }
            else
            {
                var note = UIKit.Box("result-note");
                note.Add(UIKit.Text("아직 읽히지 않는다", "result-text", Face.Hand));
                stoneResult.Add(note);
                UIKit.AnimateIn(note, "note-start", 30);
                UIKit.Shake(stone, 8f);
                AudioHub.Play("wrong", 0.35f);
            }
        }

        void ShowTranslation(bool animate)
        {
            var g = Game.I;
            stoneResult.Clear();
            var strip = UIKit.Box("translation-strip");
            UIKit.Rotate(strip, UIKit.Jitter(def.Id, 1.5f));
            strip.Add(UIKit.Box("tape tape-left"));
            foreach (var line in def.Lines)
            {
                var text = g.Data.Translate(line);
                strip.Add(UIKit.Text(string.IsNullOrEmpty(text) ? "(읽어 냈다)" : text, "translation", Face.Serif));
            }
            stoneResult.Add(strip);
            if (animate) UIKit.AnimateIn(strip, "strip-start", 30);
            RefreshAll();
        }

        public void Close() { style.display = DisplayStyle.None; }
    }
}
