using System;
using System.Linq;
using OUAT.Core;
using UnityEngine;
using UnityEngine.UIElements;

namespace OUAT.UI
{
    /// <summary>
    /// 글자를 누르면 그 옆에 붙는 종이 쪽지: 큰 글자, 추측 한 줄(직접 쓰기, 판정 대상 — 뜻-16), 메모(자유, 판정 안 함 — 뜻-25),
    /// 메모 속 후보를 눌러 추측으로 올리기, 확정 도장. Enter·바깥 누르기·Esc로 닫으면 적어 둔다.
    /// </summary>
    public class GuessPopup : VisualElement
    {
        readonly VisualElement card, seal, cands;
        readonly Image glyph;
        readonly TextField guess, memo;
        readonly Label status, seenAt;
        string word, before;
        Action changed;
        Rect anchorRect;

        public bool IsOpen => style.display == DisplayStyle.Flex;

        public GuessPopup()
        {
            AddToClassList("screen"); AddToClassList("guess-screen");
            pickingMode = PickingMode.Position;
            style.display = DisplayStyle.None;
            RegisterCallback<PointerDownEvent>(e => { if (e.target == this) Close(); });

            card = UIKit.Box("guess-card", PickingMode.Position);
            Add(card);
            card.Add(UIKit.Box("tape tape-top"));
            var top = UIKit.Box("guess-top"); card.Add(top);
            glyph = UIKit.Picture(null, "guess-glyph"); top.Add(glyph);
            var side = UIKit.Box("guess-side"); top.Add(side);
            seal = UIKit.Box("guess-seal"); side.Add(seal);
            status = UIKit.Text("", "guess-status", Face.Hand); side.Add(status);

            card.Add(UIKit.Text("뜻", "field-label", Face.Serif));
            guess = new TextField { maxLength = 20 };
            guess.AddToClassList("guess-field");
            UIKit.SetFace(guess, Face.Hand);
            card.Add(guess);
            card.Add(UIKit.Box("field-line"));

            card.Add(UIKit.Text("메모", "field-label", Face.Serif));
            memo = new TextField { multiline = true, maxLength = 300 };
            memo.AddToClassList("memo-field");
            UIKit.SetFace(memo, Face.Hand);
            card.Add(memo);
            cands = UIKit.Box("memo-cands"); card.Add(cands);
            memo.RegisterValueChangedCallback(_ => BuildCandidates());

            var foot = UIKit.Box("guess-foot"); card.Add(foot);
            seenAt = UIKit.Text("", "guess-seen", Face.Serif); foot.Add(seenAt);
            foot.Add(UIKit.BrushButton("적어 두기", Close, red: false, extra: "brush-small"));

            guess.RegisterCallback<KeyDownEvent>(e =>
            {
                if (e.keyCode == KeyCode.Return || e.keyCode == KeyCode.KeypadEnter) { Close(); e.StopPropagation(); }
            }, TrickleDown.TrickleDown);
            card.RegisterCallback<GeometryChangedEvent>(_ => Position());
        }

        public void Open(string w, VisualElement anchor, Action onChanged)
        {
            var g = Game.I;
            if (g == null || string.IsNullOrEmpty(w)) return;
            if (IsOpen) Close();
            word = w; changed = onChanged;
            var st = g.State.Word(w);
            before = st.guess ?? "";
            glyph.image = PieceView.GlyphTexture(w);
            guess.SetValueWithoutNotify(st.guess);
            memo.SetValueWithoutNotify(st.memo);
            status.text = st.confirmed ? "뜻을 알아낸 글자" : st.usedOk ? "써서 통한 적 있음\n뜻이 맞으면 확정" : "";
            seal.style.display = st.confirmed ? DisplayStyle.Flex : DisplayStyle.None;
            EnableInClassList("is-confirmed", st.confirmed);
            seenAt.text = !string.IsNullOrEmpty(st.seenAt) && g.Data.Places.TryGetValue(st.seenAt, out var p) ? $"처음 본 곳 · {p.Name}" : "";
            BuildCandidates();
            anchorRect = anchor != null && anchor.panel != null ? anchor.worldBound : new Rect(860, 440, 200, 200);
            UIKit.Rotate(card, UIKit.Jitter(w, 1.5f));
            style.display = DisplayStyle.Flex;
            Position();
            UIKit.AnimateIn(card, "guess-start", 20);
            schedule.Execute(() => guess.Focus()).StartingIn(60);
            AudioHub.Play("page", 0.3f, 1.3f);
        }

        /// <summary>글자 옆(오른쪽, 자리가 없으면 왼쪽)에 붙이고 화면 안으로 끌어들인다.</summary>
        void Position()
        {
            if (!IsOpen) return;
            float cw = card.resolvedStyle.width, ch = card.resolvedStyle.height;
            if (float.IsNaN(cw) || cw <= 1f) { cw = 460; ch = 520; }
            float W = layout.width, H = layout.height;
            if (float.IsNaN(W) || W <= 1f) { W = 1920; H = 1080; }
            float x = anchorRect.xMax + 24f;
            if (x + cw > W - 20f) x = anchorRect.xMin - cw - 24f;
            if (x < 20f) x = Mathf.Clamp(anchorRect.center.x - cw / 2f, 20f, W - cw - 20f);
            float y = Mathf.Clamp(anchorRect.center.y - ch * 0.4f, 20f, Mathf.Max(20f, H - ch - 20f));
            card.style.left = x; card.style.top = y;
        }

        void BuildCandidates()
        {
            cands.Clear();
            var parts = (memo.value ?? "").Split(new[] { ',', '/', '\n', '·', ';', '、', '，' }, StringSplitOptions.RemoveEmptyEntries)
                .Select(x => x.Trim()).Where(x => x.Length > 0 && x.Length <= 20 && x != guess.value).Distinct().Take(6).ToList();
            cands.style.display = parts.Count > 0 ? DisplayStyle.Flex : DisplayStyle.None;
            if (parts.Count == 0) return;
            cands.Add(UIKit.Text("후보 →", "cand-head", Face.Serif));
            foreach (var c in parts)
            {
                var b = UIKit.OnClick(UIKit.Box("cand"), () => { guess.value = c; BuildCandidates(); AudioHub.Play("piece", 0.3f, 1.4f); });
                b.Add(UIKit.Text(c, "cand-text", Face.Hand));
                cands.Add(b);
            }
        }

        public void Close()
        {
            if (!IsOpen) return;
            var g = Game.I;
            if (g != null && word != null)
            {
                g.State.SetMemo(word, memo.value);
                var now = (guess.value ?? "").Trim();
                if (now != before.Trim()) AudioHub.Play("quill", 0.5f);
                g.State.SetGuess(word, guess.value, g.Data.IsGuessCorrect);
            }
            guess.Blur(); memo.Blur();
            style.display = DisplayStyle.None;
            var cb = changed; changed = null;
            cb?.Invoke();
        }
    }
}
