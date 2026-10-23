using System;
using UnityEngine;
using UnityEngine.UIElements;

namespace OUAT.UI
{
    /// <summary>글꼴 셋: 책 글씨(고운바탕), 굵은 책 글씨, 손글씨(나눔손글씨 펜 — 플레이어가 쓴 추측·메모·연필 메모), 고딕(Pretendard, 예비).</summary>
    public enum Face { Serif, SerifBold, Hand, Sans }

    /// <summary>
    /// 화면 공통 도우미: 글꼴, 글자·상자 만들기, 붓 단추·잉크 글자 단추, 나타남 애니메이션, 흔들기.
    /// 글꼴 파일은 Resources/UI/Fonts/*.ttf(OFL). 없으면 Pretendard로 남는다.
    /// </summary>
    public static class UIKit
    {
        static Font serif, serifBold, hand;
        static UnityEngine.TextCore.Text.FontAsset handAsset;
        static bool loaded;
        public static UnityEngine.TextCore.Text.FontAsset SansAsset;

        static void Load()
        {
            if (loaded) return;
            loaded = true;
            serif = Resources.Load<Font>("UI/Fonts/GowunBatang-Regular");
            serifBold = Resources.Load<Font>("UI/Fonts/GowunBatang-Bold");
            hand = Resources.Load<Font>("UI/Fonts/NanumPenScript-Regular");
            // 손글씨 글꼴(나눔손글씨 펜)에는 … — · → ①②③ 같은 기호가 없다 → 고운바탕을 대신 쓰는 글꼴(fallback)로 묶은 동적 글꼴 자산을 만든다.
            // 실패하면 예전처럼 Font를 그대로 쓴다(기호만 빠질 수 있음).
            try
            {
                if (hand != null && serif != null)
                {
                    var h = UnityEngine.TextCore.Text.FontAsset.CreateFontAsset(hand);
                    var s = UnityEngine.TextCore.Text.FontAsset.CreateFontAsset(serif);
                    if (h != null && s != null)
                    {
                        if (h.fallbackFontAssetTable == null) h.fallbackFontAssetTable = new System.Collections.Generic.List<UnityEngine.TextCore.Text.FontAsset>();
                        h.fallbackFontAssetTable.Add(s);
                        handAsset = h;
                    }
                }
            }
            catch (Exception e) { Debug.LogWarning("[OUAT] 손글씨 대체 글꼴 실패: " + e.Message); handAsset = null; }
        }

        public static bool HasSerif { get { Load(); return serif != null; } }

        public static void SetFace(VisualElement e, Face f)
        {
            if (e == null) return;
            Load();
            Font font = f == Face.Serif ? serif : f == Face.SerifBold ? (serifBold ? serifBold : serif) : f == Face.Hand ? hand : null;
            if (f == Face.Hand && handAsset != null) e.style.unityFontDefinition = FontDefinition.FromSDFFont(handAsset);
            else if (font != null) e.style.unityFontDefinition = FontDefinition.FromFont(font);
            else if (f == Face.Sans && SansAsset != null) e.style.unityFontDefinition = FontDefinition.FromSDFFont(SansAsset);
            if (f == Face.SerifBold && serifBold == null) e.style.unityFontStyleAndWeight = FontStyle.Bold;
        }

        public static void AddClasses(VisualElement e, string cls)
        {
            if (string.IsNullOrEmpty(cls)) return;
            foreach (var c in cls.Split(' ')) if (c.Length > 0) e.AddToClassList(c);
        }

        public static Label Text(string text, string cls, Face face = Face.Serif)
        {
            var l = new Label(text ?? "") { pickingMode = PickingMode.Ignore };
            AddClasses(l, cls);
            SetFace(l, face);
            return l;
        }

        public static VisualElement Box(string cls, PickingMode pick = PickingMode.Ignore)
        {
            var v = new VisualElement { pickingMode = pick };
            AddClasses(v, cls);
            return v;
        }

        public static Image Picture(Texture tex, string cls)
        {
            var i = new Image { image = tex, scaleMode = ScaleMode.ScaleToFit, pickingMode = PickingMode.Ignore };
            AddClasses(i, cls);
            return i;
        }

        public static T OnClick<T>(T e, Action a) where T : VisualElement
        {
            e.pickingMode = PickingMode.Position;
            e.AddManipulator(new Clickable(() => a?.Invoke()));
            return e;
        }

        /// <summary>붓 획 위에 종이색 글자(주 행동). red = 인주색(말하기).</summary>
        public static VisualElement BrushButton(string text, Action a, bool red = false, string extra = null)
        {
            var b = Box("brush-btn" + (red ? " brush-red" : "") + (extra != null ? " " + extra : ""), PickingMode.Position);
            // 붓 획 그림(480×120)의 가로·세로 비를 지키도록 9-slice 배율을 단추 높이에 맞춘다(USS 높이: 기본 84, speak 96, small 64)
            b.style.unitySliceScale = extra != null && extra.Contains("speak") ? 0.8f : extra != null && extra.Contains("brush-small") ? 0.53f : 0.7f;
            var l = Text(text, "brush-btn-label", Face.SerifBold);
            b.Add(l);
            return OnClick(b, a);
        }

        /// <summary>잉크 글자 + 마우스를 올리면 그어지는 붓 밑줄(보조 행동).</summary>
        public static VisualElement InkButton(string text, Action a, string extra = null)
        {
            var b = Box("ink-btn" + (extra != null ? " " + extra : ""), PickingMode.Position);
            b.Add(Text(text, "ink-btn-label", Face.Serif));
            b.Add(Box("ink-btn-line"));
            return OnClick(b, a);
        }

        public static void SetEnabledLook(VisualElement e, bool on)
        {
            e.SetEnabled(on);
            e.EnableInClassList("is-off", !on);
        }

        /// <summary>시작 상태 클래스를 붙였다가 첫 배치가 끝난 다음 프레임에 떼어 USS 전환이 돌게 한다.</summary>
        public static void AnimateIn(VisualElement e, string startCls, long delayMs = 16)
        {
            if (e == null) return;
            e.AddToClassList(startCls);
            EventCallback<GeometryChangedEvent> cb = null;
            cb = _ =>
            {
                e.UnregisterCallback(cb);
                e.schedule.Execute(() => e.RemoveFromClassList(startCls)).StartingIn(delayMs);
            };
            if (e.panel != null && !float.IsNaN(e.layout.width) && e.layout.width > 0)
                e.schedule.Execute(() => e.RemoveFromClassList(startCls)).StartingIn(delayMs);
            else e.RegisterCallback(cb);
        }

        /// <summary>끝 상태 클래스를 붙이고 seconds 뒤에 떼어 낸다.</summary>
        public static void AnimateOutAndRemove(VisualElement e, string endCls, float seconds)
        {
            if (e == null) return;
            e.AddToClassList(endCls);
            e.pickingMode = PickingMode.Ignore;
            e.schedule.Execute(() => e.RemoveFromHierarchy()).StartingIn((long)(seconds * 1000));
        }

        /// <summary>좌우로 짧게 흔들기(틀린 자리에 놓음·안 읽힘).</summary>
        public static void Shake(VisualElement e, float amp = 9f)
        {
            if (e == null) return;
            float[] seq = { 1f, -0.85f, 0.6f, -0.4f, 0.2f, 0f };
            int i = 0;
            e.schedule.Execute(() =>
            {
                e.style.translate = new Translate(seq[Mathf.Min(i, seq.Length - 1)] * amp, 0);
                i++;
                if (i >= seq.Length) e.style.translate = StyleKeyword.Null;
            }).Every(40).Until(() => i >= seq.Length);
        }

        public static void Rotate(VisualElement e, float deg) => e.style.rotate = new UnityEngine.UIElements.Rotate(new Angle(deg, AngleUnit.Degree));

        /// <summary>id마다 같은 값이 나오는 작은 흔들림(손으로 붙인 느낌).</summary>
        public static float Jitter(string key, float amp)
        {
            if (string.IsNullOrEmpty(key)) return 0;
            int h = 17;
            foreach (var ch in key) h = h * 31 + ch;
            return ((h & 0xFFFF) / 65535f * 2f - 1f) * amp;
        }
    }
}
