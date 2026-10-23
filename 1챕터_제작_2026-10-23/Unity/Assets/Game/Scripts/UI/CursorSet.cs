using System.Collections.Generic;
using OUAT.Core;
using UnityEngine;

namespace OUAT.UI
{
    /// <summary>
    /// 잉크 커서(Resources/UI/cursor_*.png, 원본 48px, UI 키트). 크기: 보통 32px(원본을 줄여 새로 만듦) · 크게 48px(원본).
    /// 핫스폿 = 그림의 화살표 끝(원본 48px 기준: 기본·말·쓰기 (4,3), 걷기 = 고리 가운데 (24,30)) — 크기에 맞춰 같은 비율로 옮긴다.
    /// 운영체제가 커서 그림을 다시 늘리지 않도록 정확한 크기의 그림을 직접 만든다(“포인터가 안 맞음” 원인 제거).
    /// </summary>
    public static class CursorSet
    {
        static readonly Dictionary<string, (Texture2D tex, Vector2 hot)> cache = new Dictionary<string, (Texture2D, Vector2)>();
        static CursorKind current = (CursorKind)(-1);
        static bool currentLarge;

        public static void Apply(CursorKind kind)
        {
            bool large = GameSettings.CursorLarge;
            if (kind == current && large == currentLarge) return;
            current = kind; currentLarge = large;
            string name = kind == CursorKind.Talk ? "talk" : kind == CursorKind.Use ? "use" : kind == CursorKind.Walk ? "walk" : "default";
            var c = Get(name, large ? 48 : 32);
            Cursor.SetCursor(c.tex, c.tex ? c.hot : Vector2.zero, CursorMode.Auto);
        }

        /// <summary>설정이 바뀌면 다시 고르게.</summary>
        public static void Refresh() { var k = current; current = (CursorKind)(-1); if ((int)k >= 0) Apply(k); }

        static (Texture2D tex, Vector2 hot) Get(string name, int size)
        {
            string key = name + size;
            if (cache.TryGetValue(key, out var v)) return v;
            var src = Resources.Load<Texture2D>("UI/cursor_" + name);
            Vector2 hot48 = name == "walk" ? new Vector2(24, 30) : new Vector2(4, 3);
            if (src == null) { v = (null, Vector2.zero); cache[key] = v; return v; }
            if (size == src.width) { v = (src, hot48 * (size / 48f)); cache[key] = v; return v; }
            Texture2D dst = null;
            try { dst = Resample(src, size); } catch { dst = null; }
            if (dst == null) v = (src, hot48 * (src.width / 48f));
            else
            {
                var h = hot48 * (size / (float)src.width);
                v = (dst, new Vector2(Mathf.Round(h.x), Mathf.Round(h.y)));
            }
            cache[key] = v;
            return v;
        }

        /// <summary>미리 곱한 알파로 4×4 표본 평균(선이 번지지 않고 가장자리만 매끈).</summary>
        static Texture2D Resample(Texture2D src, int size)
        {
            if (!src.isReadable) return null;
            var dst = new Texture2D(size, size, TextureFormat.RGBA32, false) { filterMode = FilterMode.Bilinear, wrapMode = TextureWrapMode.Clamp };
            var px = new Color[size * size];
            const int S = 4;
            for (int y = 0; y < size; y++)
                for (int x = 0; x < size; x++)
                {
                    float r = 0, g = 0, b = 0, a = 0;
                    for (int sy = 0; sy < S; sy++)
                        for (int sx = 0; sx < S; sx++)
                        {
                            float u = (x + (sx + 0.5f) / S) / size, w = (y + (sy + 0.5f) / S) / size;
                            var c = src.GetPixelBilinear(u, w);
                            r += c.r * c.a; g += c.g * c.a; b += c.b * c.a; a += c.a;
                        }
                    px[y * size + x] = a > 1e-4f ? new Color(r / a, g / a, b / a, a / (S * S)) : new Color(0, 0, 0, 0);
                }
            dst.SetPixels(px);
            dst.Apply(false, false);
            return dst;
        }
    }
}
