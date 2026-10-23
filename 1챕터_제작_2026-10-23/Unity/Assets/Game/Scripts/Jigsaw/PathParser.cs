using System;
using System.Collections.Generic;
using System.Globalization;

namespace OUAT.Jigsaw
{
    /// <summary>A point in model cell space: the cell is 0..100 on both axes, y grows downwards. Tabs reach about -21..121.</summary>
    public readonly struct CellPoint : IEquatable<CellPoint>
    {
        /// <summary>Creates a point.</summary>
        public CellPoint(float x, float y)
        {
            X = x;
            Y = y;
        }

        /// <summary>Horizontal coordinate (0 = left edge of the cell, 100 = right edge).</summary>
        public float X { get; }
        /// <summary>Vertical coordinate (0 = top edge of the cell, 100 = bottom edge).</summary>
        public float Y { get; }

        /// <inheritdoc/>
        public bool Equals(CellPoint other) => X.Equals(other.X) && Y.Equals(other.Y);
        /// <inheritdoc/>
        public override bool Equals(object obj) => obj is CellPoint p && Equals(p);
        /// <inheritdoc/>
        public override int GetHashCode() => X.GetHashCode() * 397 ^ Y.GetHashCode();
        /// <inheritdoc/>
        public override string ToString() => X.ToString("0.###", CultureInfo.InvariantCulture) + "," + Y.ToString("0.###", CultureInfo.InvariantCulture);
    }

    /// <summary>
    /// Turns a model's SVG outline into polygons for Unity's Painter2D (MoveTo / LineTo / ClosePath).
    /// models.json only uses absolute <c>M</c>, <c>L</c> and <c>Z</c> with <c>x,y</c> pairs, so those are the commands
    /// supported (plus SVG's implicit repetition: extra pairs after <c>M</c> are line-tos). Anything else is rejected.
    /// To draw at board unit <c>U</c> pixels per cell (app.js uses 70), scale by <c>U / 100</c>.
    /// </summary>
    public static class PathParser
    {
        /// <summary>
        /// Parses every subpath. Each subpath is a closed polygon (the closing edge back to the first point is implied).
        /// </summary>
        /// <param name="path">SVG path data.</param>
        /// <param name="dropRepeatedPoints">
        /// When true (default), consecutive identical points and a final point equal to the first are removed;
        /// the outlines contain such repeats at tab joins and they only produce zero-length segments.
        /// </param>
        /// <exception cref="FormatException">Unsupported command or malformed numbers.</exception>
        public static IReadOnlyList<IReadOnlyList<CellPoint>> ParseSubpaths(string path, bool dropRepeatedPoints = true)
        {
            if (path == null) throw new ArgumentNullException(nameof(path));
            var result = new List<IReadOnlyList<CellPoint>>();
            List<CellPoint> current = null;
            int i = 0;
            char command = '\0';

            void Finish()
            {
                if (current == null) return;
                if (dropRepeatedPoints && current.Count > 1 && current[current.Count - 1].Equals(current[0])) current.RemoveAt(current.Count - 1);
                if (current.Count > 0) result.Add(current);
                current = null;
            }

            void Add(CellPoint p)
            {
                if (dropRepeatedPoints && current.Count > 0 && current[current.Count - 1].Equals(p)) return;
                current.Add(p);
            }

            while (true)
            {
                SkipSeparators(path, ref i);
                if (i >= path.Length) break;
                char c = path[i];
                if (char.IsLetter(c))
                {
                    i++;
                    switch (c)
                    {
                        case 'M':
                            Finish();
                            current = new List<CellPoint>();
                            Add(ReadPoint(path, ref i));
                            command = 'L'; // implicit pairs after M are line-tos
                            break;
                        case 'L':
                            if (current == null) throw new FormatException($"Path: 'L' before 'M' at {i - 1}.");
                            Add(ReadPoint(path, ref i));
                            command = 'L';
                            break;
                        case 'Z':
                        case 'z':
                            if (current == null) throw new FormatException($"Path: 'Z' before 'M' at {i - 1}.");
                            Finish();
                            command = '\0';
                            break;
                        default:
                            throw new FormatException($"Path: unsupported command '{c}' at {i - 1} (models.json uses only M, L, Z).");
                    }
                }
                else
                {
                    if (command != 'L' || current == null) throw new FormatException($"Path: coordinates without a command at {i}.");
                    Add(ReadPoint(path, ref i));
                }
            }
            Finish();
            return result;
        }

        /// <summary>Parses a path that must contain exactly one subpath (every shipped model).</summary>
        /// <exception cref="FormatException">Malformed path or not exactly one subpath.</exception>
        public static IReadOnlyList<CellPoint> ParsePolygon(string path, bool dropRepeatedPoints = true)
        {
            var subpaths = ParseSubpaths(path, dropRepeatedPoints);
            if (subpaths.Count != 1) throw new FormatException($"Path: expected one subpath, found {subpaths.Count}.");
            return subpaths[0];
        }

        private static void SkipSeparators(string s, ref int i)
        {
            while (i < s.Length && (s[i] == ' ' || s[i] == ',' || s[i] == '\t' || s[i] == '\n' || s[i] == '\r' || s[i] == '\f')) i++;
        }

        private static CellPoint ReadPoint(string s, ref int i)
        {
            float x = ReadNumber(s, ref i);
            float y = ReadNumber(s, ref i);
            return new CellPoint(x, y);
        }

        private static float ReadNumber(string s, ref int i)
        {
            SkipSeparators(s, ref i);
            int start = i;
            if (i < s.Length && (s[i] == '+' || s[i] == '-')) i++;
            int digits = 0;
            while (i < s.Length && s[i] >= '0' && s[i] <= '9') { i++; digits++; }
            if (i < s.Length && s[i] == '.')
            {
                i++;
                while (i < s.Length && s[i] >= '0' && s[i] <= '9') { i++; digits++; }
            }
            if (digits == 0) throw new FormatException($"Path: number expected at {start}.");
            if (i < s.Length && (s[i] == 'e' || s[i] == 'E'))
            {
                int mark = i;
                i++;
                if (i < s.Length && (s[i] == '+' || s[i] == '-')) i++;
                int exp = i;
                while (i < s.Length && s[i] >= '0' && s[i] <= '9') i++;
                if (i == exp) i = mark; // not an exponent after all
            }
            return float.Parse(s.Substring(start, i - start), NumberStyles.Float, CultureInfo.InvariantCulture);
        }
    }

    /// <summary>Where the trial UI (app.js <c>part()</c>) puts a piece's word, so it stays clear of socket notches.</summary>
    public static class PieceLabelLayout
    {
        /// <summary>Inset (cell units) on each side that holds a socket: 0.19 of the cell.</summary>
        public const float SocketInset = 19f;

        /// <summary>Label centre in cell space (0..100): the cell centre shifted away from socket sides.</summary>
        public static CellPoint Center(JigsawModel model)
        {
            if (model == null) throw new ArgumentNullException(nameof(model));
            Insets(model, out float l, out float r, out float t, out float b);
            return new CellPoint(50f + (l - r) / 2f, 50f + (t - b) / 2f);
        }

        /// <summary>
        /// app.js font size in pixels for a cell of <paramref name="unitPixels"/>: <c>min(20, (u - insets - 8) / word.length)</c>.
        /// Length is counted in UTF-16 units, as in JavaScript.
        /// </summary>
        public static float FontSize(JigsawModel model, string word, float unitPixels)
        {
            if (model == null) throw new ArgumentNullException(nameof(model));
            if (string.IsNullOrEmpty(word)) return 0f;
            Insets(model, out float l, out float r, out _, out _);
            float scale = unitPixels / 100f;
            return Math.Min(20f, (unitPixels - (l + r) * scale - 8f) / word.Length);
        }

        private static void Insets(JigsawModel model, out float l, out float r, out float t, out float b)
        {
            l = r = t = b = 0f;
            foreach (var s in model.SocketSides)
            {
                if (s == Side.W) l = SocketInset;
                else if (s == Side.E) r = SocketInset;
                else if (s == Side.N) t = SocketInset;
                else b = SocketInset;
            }
        }
    }
}
