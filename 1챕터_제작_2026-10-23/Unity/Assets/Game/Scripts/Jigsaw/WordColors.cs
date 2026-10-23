using System;
using System.Collections.Generic;
using System.Linq;

namespace OUAT.Jigsaw
{
    /// <summary>Word colour. Yellow = object (대상), blue = action/state (행동·상태). Chapter 1 uses only these two.</summary>
    public enum WordColor
    {
        /// <summary>Yellow (<c>"yellow"</c>): objects, places, things.</summary>
        Yellow,
        /// <summary>Blue (<c>"blue"</c>): actions and states.</summary>
        Blue,
    }

    /// <summary>
    /// Word colours. A word is blue when it is in the blue set, otherwise yellow (core.js <c>colorOf</c>).
    /// Blue sets are plain <see cref="ISet{T}"/>s; chapter data should pass its own (<see cref="BlueSetFromColors"/>).
    /// </summary>
    public static class WordColors
    {
        /// <summary>core.js <c>DEFAULT_BLUE_WORDS</c>, in source order.</summary>
        public static readonly IReadOnlyList<string> CoreDefaultBlueWords = new[]
        {
            "차갑다", "따뜻하다", "아프다", "뜨겁다", "열다", "닫다", "가다", "주다", "가지다", "오다", "멈추다", "움직이다",
            "보다", "보여주다", "말하다", "듣다", "아니다", "않다", "부정", "질문", "묻다", "원하다", "필요하다", "알다",
            "모르다", "먼저", "다음", "만", "같다", "다르다", "크다", "작다", "밝다", "어둡다", "있다", "없다", "되다",
            "괜찮다", "쓰다", "먹다", "마시다", "쉬다", "기다리다", "돕다", "건네다", "밀다", "당기다", "들어가다", "나가다",
        };

        /// <summary>state.js <c>BLUE_WORDS</c> of the 2026-10-20 green-border trial, in source order.</summary>
        public static readonly IReadOnlyList<string> TrialStateBlueWords = new[]
        {
            "떨어지다", "가져가다", "남다", "먹다", "묻다", "보다", "원하다", "가다", "마시다",
        };

        /// <summary>
        /// Shared default set used when a method receives a null blue set: <see cref="CoreDefaultBlueWords"/> plus
        /// <see cref="TrialStateBlueWords"/>. (core.js alone defaults to the core list only.) Read-only.
        /// Note: chapter-1 blue words 절하다, 고르다, 데려가다, 그리다 are NOT in it.
        /// </summary>
        public static readonly ISet<string> DefaultBlueWords = new ReadOnlySet(CoreDefaultBlueWords.Concat(TrialStateBlueWords));

        /// <summary>Creates a new mutable blue set from words (ordinal comparison, like a JavaScript <c>Set</c>).</summary>
        public static HashSet<string> CreateBlueSet(IEnumerable<string> words)
            => new HashSet<string>((words ?? throw new ArgumentNullException(nameof(words))).Where(w => w != null), StringComparer.Ordinal);

        /// <summary>Creates a blue set from words with explicit colours (the chapter's word table); only blue words are kept.</summary>
        public static HashSet<string> BlueSetFromColors(IEnumerable<KeyValuePair<string, WordColor>> wordColors)
            => CreateBlueSet((wordColors ?? throw new ArgumentNullException(nameof(wordColors))).Where(p => p.Value == WordColor.Blue).Select(p => p.Key));

        /// <summary>
        /// core.js <c>colorOf(word, blueWords)</c>: blue when the word is in the set, otherwise yellow (also for an empty word).
        /// </summary>
        /// <param name="word">The word.</param>
        /// <param name="blueWords">Blue set; null uses <see cref="DefaultBlueWords"/>.</param>
        public static WordColor ColorOf(string word, ISet<string> blueWords = null)
            => word != null && (blueWords ?? DefaultBlueWords).Contains(word) ? WordColor.Blue : WordColor.Yellow;

        /// <summary>app.js piece colour: null for an empty model (no word yet, drawn in paper colour), otherwise <see cref="ColorOf"/>.</summary>
        public static WordColor? PieceColorOf(string word, ISet<string> blueWords = null)
            => string.IsNullOrEmpty(word) ? (WordColor?)null : ColorOf(word, blueWords);

        /// <summary>Data code (<c>"yellow"</c> / <c>"blue"</c>).</summary>
        public static string Code(this WordColor color) => color == WordColor.Blue ? "blue" : "yellow";

        /// <summary>Fill hex of a piece (app.js COLORS; null colour = empty model).</summary>
        public static string FillHex(WordColor? color)
            => color == WordColor.Yellow ? "#e9c76a" : color == WordColor.Blue ? "#91bece" : "#f1eadb";

        /// <summary>Outline hex of a piece (app.js COLORS; null colour = empty model).</summary>
        public static string StrokeHex(WordColor? color)
            => color == WordColor.Yellow ? "#846b31" : color == WordColor.Blue ? "#496f80" : "#a2987d";

        /// <summary>Read-only ordinal set so the shared default cannot be modified by callers.</summary>
        private sealed class ReadOnlySet : ISet<string>
        {
            private readonly HashSet<string> inner;
            public ReadOnlySet(IEnumerable<string> words) { inner = new HashSet<string>(words, StringComparer.Ordinal); }
            public int Count => inner.Count;
            public bool IsReadOnly => true;
            public bool Contains(string item) => item != null && inner.Contains(item);
            public void CopyTo(string[] array, int arrayIndex) => inner.CopyTo(array, arrayIndex);
            public IEnumerator<string> GetEnumerator() => inner.GetEnumerator();
            System.Collections.IEnumerator System.Collections.IEnumerable.GetEnumerator() => inner.GetEnumerator();
            public bool IsProperSubsetOf(IEnumerable<string> other) => inner.IsProperSubsetOf(other);
            public bool IsProperSupersetOf(IEnumerable<string> other) => inner.IsProperSupersetOf(other);
            public bool IsSubsetOf(IEnumerable<string> other) => inner.IsSubsetOf(other);
            public bool IsSupersetOf(IEnumerable<string> other) => inner.IsSupersetOf(other);
            public bool Overlaps(IEnumerable<string> other) => inner.Overlaps(other);
            public bool SetEquals(IEnumerable<string> other) => inner.SetEquals(other);
            public bool Add(string item) => throw ReadOnly();
            void ICollection<string>.Add(string item) => throw ReadOnly();
            public void Clear() => throw ReadOnly();
            public bool Remove(string item) => throw ReadOnly();
            public void ExceptWith(IEnumerable<string> other) => throw ReadOnly();
            public void IntersectWith(IEnumerable<string> other) => throw ReadOnly();
            public void SymmetricExceptWith(IEnumerable<string> other) => throw ReadOnly();
            public void UnionWith(IEnumerable<string> other) => throw ReadOnly();
            private static NotSupportedException ReadOnly() => new NotSupportedException("DefaultBlueWords is read-only; use CreateBlueSet.");
        }
    }
}
