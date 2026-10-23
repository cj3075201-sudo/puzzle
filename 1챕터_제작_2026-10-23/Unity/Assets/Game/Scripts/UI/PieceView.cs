using System.Collections.Generic;
using OUAT.Jigsaw;
using UnityEngine;
using UnityEngine.UIElements;

namespace OUAT.UI
{
    /// <summary>
    /// 직소 조각 하나를 그린다: 모형의 외곽(홈·돌출)을 Painter2D로 채우고 손으로 그은 듯한 잉크 선(본선 + 옅은 덧선)을 두른 뒤,
    /// 글자 그림을 홈을 피한 자리에 얹는다. 빈 모형은 종이색(무색), 글자를 넣으면 그 글자 색(노랑·파랑, 직-22).
    /// 끌어 온 글자가 위에 있으면 그 색을 미리 옅게 보여 준다(PreviewColor).
    /// </summary>
    public class PieceView : VisualElement
    {
        public static readonly Color Paper = new Color32(0xF4, 0xEF, 0xE3, 0xFF);
        public static readonly Color Yellow = new Color32(0xE9, 0xC7, 0x6A, 0xFF);
        public static readonly Color Blue = new Color32(0x91, 0xBE, 0xCE, 0xFF);
        public static readonly Color Ink = new Color32(0x2B, 0x26, 0x22, 0xFF);
        public static readonly Color Seal = new Color32(0xB5, 0x45, 0x2F, 0xFF);

        public JigsawModel Model { get; private set; }
        public string Word { get; private set; }
        public string ColorName { get; private set; } = "none";
        public string PieceId;
        public int CellX, CellY;
        public float Cell;
        public bool Ghost;       // 끌기 중·놓일 자리 미리보기(반투명)
        public bool Glow;        // 방금 통한 조각
        string preview;
        bool hot;
        readonly Image glyph;
        readonly Label guess;
        static readonly Dictionary<string, Texture> glyphCache = new Dictionary<string, Texture>();

        /// <summary>끌고 있는 글자의 색(놓으면 이 색이 됨). null이면 없음.</summary>
        public string PreviewColor { get => preview; set { if (preview == value) return; preview = value; MarkDirtyRepaint(); } }
        /// <summary>강조 외곽선(놓일 대상).</summary>
        public bool Hot { get => hot; set { if (hot == value) return; hot = value; MarkDirtyRepaint(); } }

        public PieceView(JigsawModel model, float cell)
        {
            Model = model; Cell = cell;
            AddToClassList("piece");
            pickingMode = PickingMode.Position;
            style.position = Position.Absolute;
            style.width = cell; style.height = cell;
            style.overflow = Overflow.Visible;
            generateVisualContent += Draw;
            glyph = new Image { pickingMode = PickingMode.Ignore, scaleMode = ScaleMode.ScaleToFit };
            glyph.AddToClassList("piece-glyph");
            glyph.style.position = Position.Absolute;
            Add(glyph);
            guess = UIKit.Text("", "piece-guess", Face.Hand);
            guess.style.position = Position.Absolute;
            Add(guess);
            LayoutGlyph();
        }

        public void SetWord(string word, string color, string guessText = null)
        {
            Word = string.IsNullOrEmpty(word) ? null : word;
            ColorName = Word == null ? "none" : color;
            glyph.image = Word == null ? null : GlyphTexture(Word);
            glyph.style.display = Word == null ? DisplayStyle.None : DisplayStyle.Flex;
            SetGuess(guessText);
            LayoutGlyph();
            MarkDirtyRepaint();
        }

        public void SetGuess(string g, bool confirmed = false)
        {
            guess.text = string.IsNullOrEmpty(g) ? "" : g;
            guess.style.display = string.IsNullOrEmpty(g) ? DisplayStyle.None : DisplayStyle.Flex;
            guess.EnableInClassList("piece-guess-ok", confirmed);
        }

        public void SetCell(float cell) { Cell = cell; style.width = cell; style.height = cell; LayoutGlyph(); MarkDirtyRepaint(); }

        void LayoutGlyph()
        {
            if (Model == null) return;
            var c = PieceLabelLayout.Center(Model);
            float size = Cell * 0.6f;
            glyph.style.width = size; glyph.style.height = size;
            glyph.style.left = c.X / 100f * Cell - size / 2f;
            glyph.style.top = c.Y / 100f * Cell - size / 2f - Cell * 0.05f;
            guess.style.left = c.X / 100f * Cell - Cell * 0.6f;
            guess.style.width = Cell * 1.2f;
            guess.style.top = c.Y / 100f * Cell + size * 0.42f;
            guess.style.fontSize = Mathf.Max(19f, Cell * 0.27f);
        }

        /// <summary>
        /// 크리처 글자 그림(UI용). 원본 512px은 획이 가늘고(약 14px) 둘레 여백이 20% 넘게 있어서 50~60px로 줄이면
        /// 획이 1px 남짓이 되어 흐리게 보였다(팀장: "문자가 너무 안 보여").
        /// 처음 쓸 때 한 번: 384px로 줄여 읽고 → 획을 약 1.6배로 굵게(팔각 팽창, 가장자리 부드러움 유지) →
        /// 글자 둘레에 맞춰 정사각으로 잘라(여백 7%) → 256px 밉맵 텍스처(삼선형)로 만든다. 실패하면 예전 방식(밉맵 복사)으로.
        /// </summary>
        public static Texture GlyphTexture(string word)
        {
            if (string.IsNullOrEmpty(word)) return null;
            if (glyphCache.TryGetValue(word, out var t) && t != null && !(t is RenderTexture lost && !lost.IsCreated())) return t;
            var src = Resources.Load<Texture2D>("Glyphs/" + word);
            Texture result = src;
            if (src != null)
            {
                Texture bold = null;
                try { bold = MakeBold(src, word); }
                catch (System.Exception e) { Debug.LogWarning("[OUAT] 굵은 글자 실패(" + word + "): " + e.Message); }
                result = bold != null ? bold : MipCopy(src, word);
            }
            glyphCache[word] = result;
            return result;
        }

        /// <summary>글자 획 색(진한 먹).</summary>
        public static readonly Color32 GlyphInk = new Color32(0x24, 0x20, 0x1D, 0xFF);

        static Texture MipCopy(Texture2D src, string word)
        {
            try
            {
                var rt = new RenderTexture(src.width, src.height, 0, RenderTextureFormat.ARGB32, RenderTextureReadWrite.sRGB)
                {
                    useMipMap = true, autoGenerateMips = true, filterMode = FilterMode.Trilinear,
                    wrapMode = TextureWrapMode.Clamp, anisoLevel = 2, name = "glyph_" + word
                };
                rt.Create();
                var prev = RenderTexture.active;
                Graphics.Blit(src, rt);
                RenderTexture.active = prev;
                return rt;
            }
            catch (System.Exception e) { Debug.LogWarning("[OUAT] 글자 밉맵 실패: " + e.Message); return src; }
        }

        const int WorkSize = 384, OutSize = 256;

        static Texture2D MakeBold(Texture2D src, string word)
        {
            int N = WorkSize;
            var rt = RenderTexture.GetTemporary(N, N, 0, RenderTextureFormat.ARGB32, RenderTextureReadWrite.Linear);
            rt.filterMode = FilterMode.Bilinear;
            var prev = RenderTexture.active;
            Graphics.Blit(src, rt);
            RenderTexture.active = rt;
            var read = new Texture2D(N, N, TextureFormat.RGBA32, false, true);
            read.ReadPixels(new Rect(0, 0, N, N), 0, 0, false);
            read.Apply(false);
            RenderTexture.active = prev;
            RenderTexture.ReleaseTemporary(rt);
            var px = read.GetPixels32();
            UnityEngine.Object.Destroy(read);

            var a = new float[N * N];
            for (int i = 0; i < a.Length; i++) a[i] = px[i].a / 255f;
            // 팽창: 정사각 반지름 2(가로·세로 나눠서) → 십자 반지름 1 = 팔각 반지름 약 3(384px 기준, 획 약 10px → 16px)
            var b = new float[a.Length];
            MaxPass(a, b, N, 2, true); MaxPass(b, a, N, 2, false);
            Cross(a, b, N);
            // 글자 둘레
            int x0 = N, y0 = N, x1 = -1, y1 = -1;
            for (int y = 0; y < N; y++)
                for (int x = 0; x < N; x++)
                    if (b[y * N + x] > 0.12f) { if (x < x0) x0 = x; if (x > x1) x1 = x; if (y < y0) y0 = y; if (y > y1) y1 = y; }
            if (x1 < 0) return null;
            float side = Mathf.Max(x1 - x0 + 1, y1 - y0 + 1);
            side *= 1.14f;
            float cx = (x0 + x1) * 0.5f, cy = (y0 + y1) * 0.5f;
            float ox = cx - side / 2f, oy = cy - side / 2f;
            int M = OutSize;
            var outPx = new Color32[M * M];
            var ink = GlyphInk;
            for (int y = 0; y < M; y++)
                for (int x = 0; x < M; x++)
                {
                    float sx = ox + (x + 0.5f) / M * side - 0.5f, sy = oy + (y + 0.5f) / M * side - 0.5f;
                    float v = Sample(b, N, sx, sy);
                    outPx[y * M + x] = new Color32(ink.r, ink.g, ink.b, (byte)Mathf.Clamp(Mathf.RoundToInt(v * 255f), 0, 255));
                }
            var tex = new Texture2D(M, M, TextureFormat.RGBA32, true, false)
            {
                filterMode = FilterMode.Trilinear, wrapMode = TextureWrapMode.Clamp, anisoLevel = 2, name = "glyphB_" + word
            };
            tex.SetPixels32(outPx);
            tex.Apply(true, true);
            return tex;
        }

        static void MaxPass(float[] src, float[] dst, int n, int r, bool horizontal)
        {
            for (int y = 0; y < n; y++)
                for (int x = 0; x < n; x++)
                {
                    float m = 0f;
                    for (int k = -r; k <= r; k++)
                    {
                        int xx = horizontal ? x + k : x, yy = horizontal ? y : y + k;
                        if (xx < 0 || yy < 0 || xx >= n || yy >= n) continue;
                        float v = src[yy * n + xx];
                        if (v > m) m = v;
                    }
                    dst[y * n + x] = m;
                }
        }

        static void Cross(float[] src, float[] dst, int n)
        {
            for (int y = 0; y < n; y++)
                for (int x = 0; x < n; x++)
                {
                    int i = y * n + x;
                    float m = src[i];
                    if (x > 0 && src[i - 1] > m) m = src[i - 1];
                    if (x < n - 1 && src[i + 1] > m) m = src[i + 1];
                    if (y > 0 && src[i - n] > m) m = src[i - n];
                    if (y < n - 1 && src[i + n] > m) m = src[i + n];
                    dst[i] = m;
                }
        }

        static float Sample(float[] a, int n, float x, float y)
        {
            int ix = Mathf.FloorToInt(x), iy = Mathf.FloorToInt(y);
            float fx = x - ix, fy = y - iy;
            float At(int xx, int yy) => xx < 0 || yy < 0 || xx >= n || yy >= n ? 0f : a[yy * n + xx];
            return Mathf.Lerp(Mathf.Lerp(At(ix, iy), At(ix + 1, iy), fx), Mathf.Lerp(At(ix, iy + 1), At(ix + 1, iy + 1), fx), fy);
        }

        public static Color FillOf(string color) => color == "yellow" ? Yellow : color == "blue" ? Blue : Paper;

        // 색연필(가방 속 사람 물건): 옅은 바탕 칠 + 빗금. 노랑·파랑 구분(직-22)은 그대로, 납작한 칠 대신 손 빗금.
        public static readonly Color WashYellow = new Color32(0xF3, 0xE2, 0xA9, 0xFF);
        public static readonly Color WashBlue = new Color32(0xD3, 0xE3, 0xEE, 0xFF);
        public static readonly Color PencilYellow = new Color32(0xC9, 0x8F, 0x1C, 0xFF);
        public static readonly Color PencilBlue = new Color32(0x36, 0x6C, 0xA4, 0xFF);
        public static readonly Color NotePaper = new Color32(0xF8, 0xF3, 0xE7, 0xFF);
        static Color WashOf(string c) => c == "yellow" ? WashYellow : c == "blue" ? WashBlue : NotePaper;
        static Color HatchOf(string c) => c == "yellow" ? PencilYellow : c == "blue" ? PencilBlue : Color.clear;

        void Draw(MeshGenerationContext ctx)
        {
            if (Model?.Outline == null) return;
            var p = ctx.painter2D;
            float s = Cell / 100f;
            string col = preview ?? ColorName;
            var fill = WashOf(col);
            var hatch = HatchOf(col);
            if (preview != null) { fill = Color.Lerp(WashOf(ColorName), fill, 0.75f); hatch.a = 0.75f; }
            if (Ghost) { fill.a = 0.5f; hatch.a *= 0.5f; }
            float lw = Mathf.Max(1.8f, Cell * 0.022f);
            foreach (var poly in Model.Outline)
            {
                if (poly.Count < 3) continue;
                // 종이 조각이 공책 위에 살짝 뜬 그늘(한쪽으로만, 옅게)
                if (!Ghost)
                {
                    p.fillColor = new Color(0.25f, 0.2f, 0.14f, 0.12f);
                    Path(p, poly, s, 2f, 3f); p.Fill();
                }
                p.fillColor = fill;
                Path(p, poly, s, 0, 0);
                p.Fill();
                if (hatch.a > 0.01f) Hatch(p, poly, s, hatch);
                // 본선(연필보다 진한 먹, 조금 흔들림 없이 — 모양 판정이 보여야 함)
                p.strokeColor = Glow ? new Color32(0xC8, 0x90, 0x2E, 0xFF) : hot ? Seal : (Ghost ? new Color(Ink.r, Ink.g, Ink.b, 0.5f) : Ink);
                p.lineWidth = Glow || hot ? lw * 1.7f : lw;
                p.lineJoin = LineJoin.Round;
                Path(p, poly, s, 0, 0);
                p.Stroke();
                // 한 번 더 그은 옅은 연필 덧선(손맛)
                if (!Ghost)
                {
                    p.strokeColor = new Color(Ink.r, Ink.g, Ink.b, 0.2f);
                    p.lineWidth = lw * 0.5f;
                    Path(p, poly, s, 1.1f, -0.8f);
                    p.Stroke();
                }
            }
        }

        /// <summary>조각 모양 안쪽만 사선 빗금(색연필). 빗금선마다 외곽과의 교점을 짝지어 안쪽 구간만 긋는다(짝-홀 규칙).</summary>
        void Hatch(Painter2D p, IReadOnlyList<CellPoint> poly, float s, Color c)
        {
            float spacing = Mathf.Max(5f, Cell * 0.075f);
            float ang = -58f * Mathf.Deg2Rad;
            var d = new Vector2(Mathf.Cos(ang), Mathf.Sin(ang));
            var nrm = new Vector2(-d.y, d.x);
            // 외곽 점(픽셀)
            int n = poly.Count;
            var pts = new Vector2[n];
            float kmin = float.MaxValue, kmax = float.MinValue;
            for (int i = 0; i < n; i++)
            {
                pts[i] = new Vector2(poly[i].X * s, poly[i].Y * s);
                float k = Vector2.Dot(pts[i], nrm);
                if (k < kmin) kmin = k; if (k > kmax) kmax = k;
            }
            p.lineCap = LineCap.Round;
            var ts = new List<float>(8);
            int line = 0;
            int seed = (PieceId ?? Model.Id ?? "").GetHashCode();
            for (float k = kmin + spacing * 0.6f; k < kmax; k += spacing, line++)
            {
                ts.Clear();
                var o = nrm * k;
                for (int i = 0, j = n - 1; i < n; j = i++)
                {
                    // 선 o + t·d 와 변 pts[j]→pts[i]의 교점
                    var a = pts[j]; var b = pts[i];
                    float ka = Vector2.Dot(a, nrm) - k, kb = Vector2.Dot(b, nrm) - k;
                    if ((ka > 0) == (kb > 0)) continue;
                    float u = ka / (ka - kb);
                    var q = a + (b - a) * u;
                    ts.Add(Vector2.Dot(q - o, d));
                }
                if (ts.Count < 2) continue;
                ts.Sort();
                float r1 = Hash(seed, line) , r2 = Hash(seed + 7, line);
                p.strokeColor = new Color(c.r, c.g, c.b, c.a * (0.42f + 0.22f * r1));
                p.lineWidth = Mathf.Max(1.2f, Cell * (0.013f + 0.006f * r2));
                for (int m = 0; m + 1 < ts.Count; m += 2)
                {
                    float t0 = ts[m] + 2.5f + 4f * r1, t1 = ts[m + 1] - 2.5f - 4f * r2;
                    if (t1 - t0 < 4f) continue;
                    p.BeginPath();
                    p.MoveTo(o + d * t0);
                    p.LineTo(o + d * t1);
                    p.Stroke();
                }
            }
        }

        static float Hash(int a, int b) { float v = Mathf.Sin(a * 0.0137f + b * 12.9898f) * 43758.5453f; return v - Mathf.Floor(v); }

        static void Path(Painter2D p, IReadOnlyList<CellPoint> poly, float s, float dx, float dy)
        {
            p.BeginPath();
            p.MoveTo(new Vector2(poly[0].X * s + dx, poly[0].Y * s + dy));
            for (int i = 1; i < poly.Count; i++) p.LineTo(new Vector2(poly[i].X * s + dx, poly[i].Y * s + dy));
            p.ClosePath();
        }

        /// <summary>점이 조각 모양 안에 있나(홈 부분을 눌러도 이웃 조각이 잡히지 않게).</summary>
        public bool ContainsLocal(Vector2 local)
        {
            if (Model?.Outline == null) return false;
            float s = Cell / 100f;
            foreach (var poly in Model.Outline)
            {
                bool inside = false;
                for (int i = 0, j = poly.Count - 1; i < poly.Count; j = i++)
                {
                    float xi = poly[i].X * s, yi = poly[i].Y * s, xj = poly[j].X * s, yj = poly[j].Y * s;
                    if ((yi > local.y) != (yj > local.y) && local.x < (xj - xi) * (local.y - yi) / (yj - yi + 1e-5f) + xi) inside = !inside;
                }
                if (inside) return true;
            }
            return false;
        }

        public override bool ContainsPoint(Vector2 localPoint) => ContainsLocal(localPoint);
    }
}
