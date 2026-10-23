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
    /// 퍼즐이 아닌 글(화-11, 뜻-28 ②): 크리처 글자가 손으로 쓴 낱말처럼 한 줄로 늘어서고, 내 추측이 있으면 글자 밑에 작게 손글씨로.
    /// 쓰인 낱말을 모두 확정했고 번역이 있으면 번역 문장으로 바뀐다. 직소 조각은 그리지 않는다.
    /// </summary>
    public class GlyphLine : VisualElement
    {
        public readonly string SentenceId;
        public Action<string, VisualElement> GlyphClicked;
        public bool ShowingTranslation { get; private set; }
        readonly bool allowTranslation;
        readonly VisualElement row;
        readonly Label translation;
        readonly List<(string word, Label guess)> cells = new List<(string, Label)>();
        readonly List<string> words = new List<string>();
        string tr;

        string place;
        bool seenMarked;

        /// <param name="markSeen">false면 낱말을 “봄”으로 적지 않는다(머리 위 말: 실제로 보이는 거리 안에 들어왔을 때 MarkSeen()을 부른다).</param>
        public GlyphLine(string sentenceId, float glyphSize, bool allowTranslation = true, bool clickable = false, string place = null, bool markSeen = true)
        {
            SentenceId = sentenceId;
            this.allowTranslation = allowTranslation;
            AddToClassList("glyph-line");
            pickingMode = PickingMode.Ignore;
            row = UIKit.Box("gl-row");
            Add(row);
            translation = UIKit.Text("", "gl-translation", Face.Serif);
            translation.style.fontSize = Mathf.Clamp(glyphSize * 0.62f, 18f, 40f);
            translation.style.display = DisplayStyle.None;
            Add(translation);

            var g = Game.I;
            if (g == null || string.IsNullOrEmpty(sentenceId) || !g.Data.Sentences.TryGetValue(sentenceId, out var spec)) return;
            tr = g.Data.Translate(sentenceId);
            int i = 0;
            foreach (var w in Flatten(spec))
            {
                var cell = UIKit.Box("gl-cell", clickable ? PickingMode.Position : PickingMode.Ignore);
                // 손으로 쓴 줄처럼 글자마다 높이·기울기가 조금씩 다르다
                cell.style.translate = new Translate(0, UIKit.Jitter(sentenceId + i, glyphSize * 0.05f));
                var img = UIKit.Picture(PieceView.GlyphTexture(w), "gl-glyph");
                img.style.width = glyphSize; img.style.height = glyphSize;
                UIKit.Rotate(img, UIKit.Jitter(w + i, 4f));
                cell.Add(img);
                var gl = UIKit.Text("", "gl-guess", Face.Hand);
                gl.style.fontSize = Mathf.Clamp(glyphSize * 0.42f, 20f, 32f);
                gl.style.minHeight = Mathf.Clamp(glyphSize * 0.42f, 20f, 32f) + 2f;
                cell.Add(gl);
                if (clickable)
                {
                    cell.AddToClassList("gl-click");
                    var word = w;
                    cell.RegisterCallback<ClickEvent>(e => { GlyphClicked?.Invoke(word, cell); e.StopPropagation(); });
                }
                row.Add(cell);
                cells.Add((w, gl));
                if (!words.Contains(w)) words.Add(w);
                i++;
            }
            this.place = place;
            if (markSeen) MarkSeen();
            Refresh();
        }

        /// <summary>이 줄의 낱말과 문장을 “봄”으로 적는다(한 번만).</summary>
        public void MarkSeen()
        {
            if (seenMarked || words.Count == 0) return;
            seenMarked = true;
            UIRoot.NoteSeen(SentenceId, words, place ?? World.PlaceZone.Current);
        }

        public void Refresh()
        {
            var g = Game.I;
            if (g == null) return;
            bool all = words.Count > 0 && words.All(w => g.State.Word(w).confirmed);
            bool tra = allowTranslation && all && !string.IsNullOrEmpty(tr);
            if (tra != ShowingTranslation)
            {
                ShowingTranslation = tra;
                row.style.display = tra ? DisplayStyle.None : DisplayStyle.Flex;
                translation.style.display = tra ? DisplayStyle.Flex : DisplayStyle.None;
                translation.text = tr ?? "";
            }
            if (tra) return;
            foreach (var (w, l) in cells)
            {
                var st = g.State.Word(w);
                string t = st.confirmed ? (string.IsNullOrEmpty(st.guess) ? w : st.guess) : st.guess ?? "";
                if (l.text != t) l.text = t;
                l.EnableInClassList("gl-guess-ok", st.confirmed);
            }
        }

        /// <summary>문장 트리를 읽는 순서(앞에서부터, 갈래는 차례로)로 낱말을 늘어놓는다. 같은 낱말이 두 번 나오면 두 번.</summary>
        public static IEnumerable<string> Flatten(SpecNode n)
        {
            if (n == null) yield break;
            if (!string.IsNullOrEmpty(n.Word)) yield return n.Word;
            foreach (var c in n.Children) foreach (var w in Flatten(c)) yield return w;
        }
    }
}
