using System;
using OUAT.Core;
using UnityEngine;
using UnityEngine.UIElements;

namespace OUAT.UI
{
    /// <summary>
    /// 왕의 띠 벗기기(대본 4-2 장치3): 그림판에 붙은 띠를 가까이 본 화면.
    /// 띠의 들뜬 오른쪽 모서리를 누른 채 왼쪽으로 끌면 띠가 오른쪽부터 접혀 넘어온다(스티커 벗기기).
    /// 넘어온 쪽 = 띠의 뒷면 = 사람 글(humanTex). 세로 축으로 접히므로 뒷면 글씨는 바로 읽힌다.
    /// 접기 계산: 끈 거리 k → 접힌 선 f = W − k/2, 손 자리 h = W − k.
    ///   띠 앞면은 [0, f]만 남고, 뒷면은 [h, f]에 보이며 그 안의 그림은 뒷면 그림의 [0, W − f] 부분(왼쪽 끝이 h에 붙음).
    ///   띠가 떨어진 자리 [f, W]에는 붙어 있던 판(밑바탕)이 드러난다.
    /// 손을 떼면: 반 넘게 젖혔으면 끝까지 넘어간 뒤 뒤집힌 띠가 제자리로 미끄러져 와 사람 글 전체가 보이고, 아니면 도로 붙는다.
    /// 글자 안내 없음 — 들뜬 모서리가 떨리고 작은 붓 화살표만.
    /// </summary>
    public class DecreeScreen : VisualElement
    {
        readonly VisualElement strip;
        GlyphLine stripLine;
        /// <summary>띠 밑 글자 줄의 글자를 눌렀을 때(UIRoot가 추측 쪽지를 연결).</summary>
        public Action<string, VisualElement> GlyphClicked;
        readonly VisualElement stage, under, bandClip, band, flapClip, flapInner, flapShadow, foldShadow, corner, cornerArrow, closeX;
        readonly Image bandImg, backImg;
        readonly Label backText;
        float W = 1320f, H = 462f;
        float k;                 // 끈 거리(px, 0..2W)
        bool dragging, done, hinted, finishing;
        float dragStartX, kAtStart;
        int pointer = -1;
        Action closed;
        IVisualElementScheduledItem wiggle, anim;

        public bool IsOpen => style.display == DisplayStyle.Flex;
        /// <summary>띠를 끝까지 벗겼나(사람 글이 다 드러남).</summary>
        public bool Peeled => done;

        public DecreeScreen()
        {
            AddToClassList("screen"); AddToClassList("decree-screen");
            pickingMode = PickingMode.Position;
            style.display = DisplayStyle.None;
            RegisterCallback<PointerDownEvent>(e => { if (e.target == this && done) Close(); });
            Add(UIKit.Box("vignette"));

            stage = UIKit.Box("decree-stage", PickingMode.Position); Add(stage);
            // 띠의 크리처 글 한 줄(항상) — 띠 그림 밑, 사람 글과 글자를 견주어 보게
            strip = UIKit.Box("decree-strip", PickingMode.Position); stage.Add(strip);
            UIKit.Rotate(strip, -0.6f);
            under = UIKit.Box("decree-under"); stage.Add(under);                 // 띠가 붙어 있던 판
            foldShadow = UIKit.Box("decree-fold-shadow"); stage.Add(foldShadow);  // 접힌 자리가 판에 드리우는 그늘
            bandClip = UIKit.Box("decree-band-clip"); stage.Add(bandClip);       // 띠 앞면(남은 부분만)
            band = UIKit.Box("decree-band"); bandClip.Add(band);
            bandImg = new Image { scaleMode = ScaleMode.StretchToFill, pickingMode = PickingMode.Ignore };
            bandImg.AddToClassList("decree-fill"); band.Add(bandImg);
            flapShadow = UIKit.Box("decree-flap-shadow"); stage.Add(flapShadow); // 넘어온 쪽이 앞면에 드리우는 그늘
            flapClip = UIKit.Box("decree-flap-clip"); stage.Add(flapClip);       // 뒷면(사람 글)
            flapInner = UIKit.Box("decree-flap"); flapClip.Add(flapInner);
            backImg = new Image { scaleMode = ScaleMode.StretchToFill, pickingMode = PickingMode.Ignore };
            backImg.AddToClassList("decree-fill"); flapInner.Add(backImg);
            backText = UIKit.Text("", "decree-human-text", Face.Hand); flapInner.Add(backText);
            corner = UIKit.Box("decree-corner"); stage.Add(corner);              // 들뜬 모서리(잡을 곳)
            cornerArrow = UIKit.Box("decree-arrow"); stage.Add(cornerArrow);
            closeX = UIKit.OnClick(UIKit.Box("close-x decree-close"), Close); stage.Add(closeX);

            stage.RegisterCallback<PointerDownEvent>(OnDown);
            stage.RegisterCallback<PointerMoveEvent>(OnMove);
            stage.RegisterCallback<PointerUpEvent>(OnUp);
            stage.RegisterCallback<PointerCaptureOutEvent>(_ => { if (dragging) Release(); });
        }

        static Texture2D Load(string name)
        {
            if (string.IsNullOrEmpty(name)) return null;
            var t = Resources.Load<Texture2D>(name);
            if (t == null && !name.StartsWith("Pictures/")) t = Resources.Load<Texture2D>("Pictures/" + name);
            return t;
        }

        /// <param name="bandTex">띠 앞면 그림(Resources 경로 또는 Pictures/ 아래 이름, 예: decree_band)</param>
        /// <param name="humanTex">띠 뒷면 = 사람 글 그림(예: decree_human). 앞면과 같은 크기·같은 찢긴 모양이어야 맞물린다.</param>
        /// <param name="bandSentence">띠 그림이 없을 때 대신 띠 위에 그릴 크리처 문장 id(선택)</param>
        /// <param name="humanText">사람 글 그림이 없을 때 뒷면에 대신 쓸 손글씨 본문(선택)</param>
        public void Open(string bandTex, string humanTex, string bandSentence, string humanText, Action onClosed)
        {
            closed = onClosed;
            var bt = Load(bandTex);
            var ht = Load(humanTex);
            float aspect = bt != null ? bt.width / (float)bt.height : ht != null ? ht.width / (float)ht.height : 2.86f;
            W = 1400f; H = W / aspect;
            if (H > 640f) { H = 640f; W = H * aspect; }
            stage.style.width = W; stage.style.height = H;
            stage.style.left = Length.Percent(50); stage.style.top = Length.Percent(50);
            stage.style.marginLeft = -W / 2f; stage.style.marginTop = -H / 2f - 10f;
            foreach (var e in new[] { under, band, flapInner }) { e.style.width = W; e.style.height = H; }
            foreach (var e in new[] { bandClip, flapClip, flapShadow, foldShadow }) e.style.height = H;

            bandImg.image = bt;
            bandImg.style.display = bt ? DisplayStyle.Flex : DisplayStyle.None;
            band.EnableInClassList("decree-band-fallback", bt == null);
            band.Query<GlyphLine>().ForEach(x => x.RemoveFromHierarchy());
            bool hasLine = Game.I != null && !string.IsNullOrEmpty(bandSentence) && Game.I.Data.Sentences.ContainsKey(bandSentence);
            if (bt == null && hasLine)
                band.Add(new GlyphLine(bandSentence, Mathf.Min(120f, H * 0.4f), allowTranslation: false));
            strip.Clear(); stripLine = null;
            strip.style.display = hasLine ? DisplayStyle.Flex : DisplayStyle.None;
            if (hasLine)
            {
                stripLine = new GlyphLine(bandSentence, 88f, allowTranslation: false, clickable: true);
                var line = stripLine;
                line.GlyphClicked = (w, el) => GlyphClicked?.Invoke(w, el);
                strip.Add(line);
                strip.style.top = H + 26f;
            }
            if (hasLine) stage.style.marginTop = -H / 2f - 92f;   // 글자 줄 자리만큼 위로

            backImg.image = ht;
            backImg.style.display = ht ? DisplayStyle.Flex : DisplayStyle.None;
            flapInner.EnableInClassList("decree-flap-fallback", ht == null);
            backText.text = ht ? "" : (humanText ?? "");
            backText.style.display = !ht && !string.IsNullOrEmpty(humanText) ? DisplayStyle.Flex : DisplayStyle.None;

            k = 0; done = false; dragging = false; hinted = false; finishing = false; pointer = -1;
            anim?.Pause(); anim = null;
            flapClip.style.translate = StyleKeyword.Null; flapClip.style.rotate = StyleKeyword.Null;
            bandClip.style.display = DisplayStyle.Flex;
            closeX.style.display = DisplayStyle.None;
            Apply();
            style.display = DisplayStyle.Flex;
            UIKit.AnimateIn(stage, "page-start", 20);
            AudioHub.Play("page", 0.45f, 0.85f);
            wiggle?.Pause();
            float t0 = Time.unscaledTime;
            wiggle = corner.schedule.Execute(() =>
            {
                if (dragging || done || finishing) return;
                float t = Time.unscaledTime - t0;
                float w = Mathf.Sin(t * 9f) * Mathf.Max(0f, Mathf.Sin(t * 1.6f)) * 5f;   // 바람에 들썩이듯 가끔
                corner.style.rotate = new UnityEngine.UIElements.Rotate(new Angle(w, AngleUnit.Degree));
                cornerArrow.style.translate = new Translate(-Mathf.Abs(Mathf.Sin(t * 2.2f)) * 12f, 0);
            }).Every(16);
        }

        void OnDown(PointerDownEvent e)
        {
            if (done || finishing || e.button != 0) return;
            var local = stage.WorldToLocal(e.position);
            float hand = W - k;
            // 잡을 곳: 손 자리(넘어온 쪽 왼쪽 끝) 둘레, 또는 아직 안 젖혔으면 띠 오른쪽 40%
            bool near = Mathf.Abs(local.x - hand) < 150f || (k < 4f && local.x > W * 0.6f);
            if (!near || local.y < -40f || local.y > H + 40f) return;
            dragging = true; pointer = e.pointerId;
            dragStartX = e.position.x; kAtStart = k;
            anim?.Pause(); anim = null;
            stage.CapturePointer(e.pointerId);
            hinted = true;
            AudioHub.Play("page", 0.35f, 1.25f);
            e.StopPropagation();
        }

        void OnMove(PointerMoveEvent e)
        {
            if (!dragging || e.pointerId != pointer) return;
            k = Mathf.Clamp(kAtStart + (dragStartX - e.position.x), 0f, 2f * W);
            Apply();
        }

        void OnUp(PointerUpEvent e)
        {
            if (!dragging || e.pointerId != pointer) return;
            if (stage.HasPointerCapture(pointer)) stage.ReleasePointer(pointer);
            Release();
        }

        void Release()
        {
            dragging = false; pointer = -1;
            if (W - k / 2f < W * 0.5f) Finish(); else SpringBack();
        }

        void SpringBack()
        {
            float from = k, t0 = Time.unscaledTime;
            anim?.Pause();
            anim = stage.schedule.Execute(() =>
            {
                float u = Mathf.Clamp01((Time.unscaledTime - t0) / 0.32f);
                k = Mathf.Lerp(from, 0f, 1f - (1f - u) * (1f - u));
                Apply();
                if (u >= 1f) { anim?.Pause(); anim = null; }
            }).Every(16);
            AudioHub.Play("piece", 0.3f, 0.8f);
        }

        void Finish()
        {
            finishing = true;
            float from = k, t0 = Time.unscaledTime;
            anim?.Pause();
            AudioHub.Play("page", 0.6f, 0.75f);
            anim = stage.schedule.Execute(() =>
            {
                float t = Time.unscaledTime - t0;
                if (t < 0.3f)
                {
                    float u = t / 0.3f;   // 끝까지 넘김
                    k = Mathf.Lerp(from, 2f * W, u * u);
                    Apply();
                    return;
                }
                k = 2f * W; Apply();
                bandClip.style.display = DisplayStyle.None;
                flapShadow.style.display = DisplayStyle.None; foldShadow.style.display = DisplayStyle.None;
                // 뒤집힌 띠(사람 글)가 제자리로 미끄러져 옴 — 판 위에 내려놓듯 살짝 들렸다 놓임
                float v = Mathf.Clamp01((t - 0.3f) / 0.42f);
                float e = 1f - (1f - v) * (1f - v) * (1f - v);
                flapClip.style.translate = new Translate(W * e, -Mathf.Sin(v * Mathf.PI) * 30f);
                flapClip.style.rotate = new UnityEngine.UIElements.Rotate(new Angle(Mathf.Sin(v * Mathf.PI) * -2.5f, AngleUnit.Degree));
                if (v >= 1f)
                {
                    anim?.Pause(); anim = null;
                    finishing = false; done = true;
                    flapClip.style.rotate = StyleKeyword.Null;
                    closeX.style.display = DisplayStyle.Flex;
                    UIKit.AnimateIn(closeX, "note-start", 250);
                }
            }).Every(16);
        }

        /// <summary>끈 거리 k에 맞춰 앞면·뒷면·그늘 자리를 놓는다.</summary>
        void Apply()
        {
            float f = Mathf.Clamp(W - k / 2f, 0f, W);   // 접힌 선
            float fw = W - f;                             // 넘어온 쪽 너비(= 드러난 판 너비)
            float hand = f - fw;                          // 손 자리
            bandClip.style.width = f;
            bool any = fw > 1f;
            flapClip.style.display = any ? DisplayStyle.Flex : DisplayStyle.None;
            flapClip.style.left = hand; flapClip.style.width = fw;   // 안쪽 그림은 left 0 그대로 → 뒷면 [0, fw]가 보임
            flapShadow.style.display = any && !done ? DisplayStyle.Flex : DisplayStyle.None;
            flapShadow.style.left = hand - 22f; flapShadow.style.width = 22f;
            foldShadow.style.display = any && !done ? DisplayStyle.Flex : DisplayStyle.None;
            foldShadow.style.left = f; foldShadow.style.width = Mathf.Min(80f, fw + 12f);
            bool idle = !any && !done && !finishing;
            corner.style.display = idle ? DisplayStyle.Flex : DisplayStyle.None;
            cornerArrow.style.display = idle && !hinted ? DisplayStyle.Flex : DisplayStyle.None;
        }

        /// <summary>자동 완주용: 끌지 않고 끝까지 벗김.</summary>
        public void DevPeel() { if (IsOpen && !done && !finishing) Finish(); }

        /// <summary>추측을 고친 뒤 글자 밑 손글씨를 새로.</summary>
        public void RefreshLine() => stripLine?.Refresh();

        public void Close()
        {
            if (!IsOpen) return;
            wiggle?.Pause(); anim?.Pause(); anim = null;
            if (dragging && pointer >= 0 && stage.HasPointerCapture(pointer)) stage.ReleasePointer(pointer);
            dragging = false; finishing = false;
            style.display = DisplayStyle.None;
            var cb = closed; closed = null;
            cb?.Invoke();
        }
    }
}
