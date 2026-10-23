using System;
using System.Collections.Generic;
using System.Linq;
using OUAT.Core;
using OUAT.Jigsaw;
using UnityEngine;
using UnityEngine.UIElements;

namespace OUAT.UI
{
    /// <summary>
    /// 이미 조립된 문장(크리처의 말·새김·머리 위 말)을 읽기 전용으로 보여 준다(직-24). 글자 밑에 내 추측 한 줄(뜻-23).
    /// 글자를 누르면 추측을 쓰는 창이 열린다.
    /// </summary>
    public class ReadBoard : VisualElement
    {
        public readonly List<PieceView> Pieces = new List<PieceView>();
        public IReadOnlyList<string> Words => Pieces.Where(p => p.Word != null).Select(p => p.Word).ToList();
        public Action<string, VisualElement> GlyphClicked;
        readonly bool showGuesses;

        public ReadBoard(SpecNode spec, float cell, bool showGuesses = true, bool clickable = true)
        {
            this.showGuesses = showGuesses;
            AddToClassList("read-board");
            pickingMode = PickingMode.Ignore;
            var g = Game.I;
            if (spec == null || g == null) return;
            List<Piece> built;
            try { built = JigsawCore.Build(spec, g.Models, g.Blue); }
            catch (Exception e) { Add(new Label("(문장을 그릴 수 없음: " + e.Message + ")")); return; }
            int minX = built.Min(p => p.X), minY = built.Min(p => p.Y);
            int maxX = built.Max(p => p.X), maxY = built.Max(p => p.Y);
            float pad = cell * 0.25f;
            style.width = (maxX - minX + 1) * cell + pad * 2;
            style.height = (maxY - minY + 1) * cell + pad * 2 + (showGuesses ? cell * 0.18f : 0);
            foreach (var p in built)
            {
                if (!g.Models.Models.TryGetValue(p.ModelId, out var m)) continue;
                var v = new PieceView(m, cell) { PieceId = p.Id, CellX = p.X, CellY = p.Y };
                v.style.left = (p.X - minX) * cell + pad;
                v.style.top = (p.Y - minY) * cell + pad;
                v.SetWord(p.Word, JigsawCore.ColorOf(p.Word, g.Blue));
                if (showGuesses && p.Word != null) v.SetGuess(GuessText(p.Word), g.State.Word(p.Word).confirmed);
                v.pickingMode = clickable ? PickingMode.Position : PickingMode.Ignore;
                if (clickable && p.Word != null)
                {
                    var word = p.Word;
                    v.RegisterCallback<ClickEvent>(e => { GlyphClicked?.Invoke(word, v); e.StopPropagation(); });
                    v.AddToClassList("clickable");
                }
                Add(v); Pieces.Add(v);
            }
        }

        public static string GuessText(string word)
        {
            var g = Game.I;
            if (g == null || string.IsNullOrEmpty(word)) return null;
            var w = g.State.Word(word);
            if (w.confirmed) return w.guess.Length > 0 ? w.guess : word;
            return string.IsNullOrEmpty(w.guess) ? "?" : w.guess;
        }

        /// <summary>추측이 없으면 빈칸(“?”를 쓰지 않음) — 머리 위 말·칩 아래처럼 비워 두는 자리.</summary>
        public static string GuessOrBlank(string word)
        {
            var g = Game.I;
            if (g == null || string.IsNullOrEmpty(word)) return "";
            var w = g.State.Word(word);
            if (w.confirmed) return w.guess.Length > 0 ? w.guess : word;
            return w.guess ?? "";
        }

        public void RefreshGuesses()
        {
            if (!showGuesses) return;
            var g = Game.I;
            foreach (var p in Pieces) if (p.Word != null) p.SetGuess(GuessText(p.Word), g != null && g.State.Word(p.Word).confirmed);
        }
    }
}
