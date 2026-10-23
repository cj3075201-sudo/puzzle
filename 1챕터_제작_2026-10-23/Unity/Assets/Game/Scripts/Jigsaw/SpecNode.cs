using System;
using System.Collections;
using System.Collections.Generic;
using System.Linq;
using System.Text;

namespace OUAT.Jigsaw
{
    /// <summary>Thrown when a spec does not have the shape core.js <c>asTree</c> accepts. Message is the core.js message.</summary>
    public sealed class SpecFormatException : Exception
    {
        /// <summary>core.js message for an array without a leading word.</summary>
        public const string NeedsWordMessage = "표현에는 글자가 필요합니다.";
        /// <summary>core.js message for anything else malformed.</summary>
        public const string BadStructureMessage = "표현 구조를 확인해 주세요.";

        /// <summary>Creates the exception.</summary>
        public SpecFormatException(string message) : base(message) { }
    }

    /// <summary>
    /// A sentence tree (core.js <c>asTree</c> result): a word and the words it connects to.
    /// Spec JSON forms: <c>"몸"</c>, <c>["밖",["몸"]]</c> (first element the word, the rest children), or <c>{"word":"밖","children":[...]}</c>.
    /// A linear chain 밖→몸→절하다→안→몸 is <c>["밖",["몸",["절하다",["안",["몸"]]]]]</c>.
    /// </summary>
    public sealed class SpecNode
    {
        /// <summary>Creates a node.</summary>
        public SpecNode(string word, IEnumerable<SpecNode> children = null)
        {
            Word = word ?? throw new ArgumentNullException(nameof(word));
            var list = children?.ToList() ?? new List<SpecNode>();
            if (list.Any(c => c == null)) throw new ArgumentException("Children cannot be null.", nameof(children));
            Children = list;
        }

        /// <summary>The word of this node.</summary>
        public string Word { get; }

        /// <summary>Connected words (joint direction: this node's tab into the child's socket).</summary>
        public IReadOnlyList<SpecNode> Children { get; }

        /// <summary>Number of nodes in the tree.</summary>
        public int Size => 1 + Children.Sum(c => c.Size);

        /// <summary>Shorthand constructor: <c>SpecNode.Of("밖", SpecNode.Of("몸"))</c>.</summary>
        public static SpecNode Of(string word, params SpecNode[] children) => new SpecNode(word, children);

        /// <summary>Builds a linear chain (each word connects to the next): <c>Chain("밖","몸","절하다")</c> = 밖→몸→절하다.</summary>
        public static SpecNode Chain(params string[] words)
        {
            if (words == null || words.Length == 0) throw new ArgumentException("A chain needs at least one word.", nameof(words));
            SpecNode node = null;
            for (int i = words.Length - 1; i >= 0; i--) node = node == null ? Of(words[i]) : Of(words[i], node);
            return node;
        }

        /// <summary>Parses spec JSON text.</summary>
        /// <exception cref="FormatException">Invalid JSON.</exception>
        /// <exception cref="SpecFormatException">Valid JSON but not a spec.</exception>
        public static SpecNode Parse(string json) => FromJson(MiniJson.ParseNode(json));

        /// <summary>
        /// core.js <c>asTree(spec)</c>. Accepts the output of <see cref="MiniJson.Parse"/> (string / <c>List&lt;object&gt;</c> /
        /// <c>Dictionary&lt;string,object&gt;</c>), a <see cref="JsonNode"/>, or an existing <see cref="SpecNode"/>.
        /// </summary>
        /// <exception cref="SpecFormatException">Not a spec (same messages as core.js).</exception>
        public static SpecNode FromJson(object node)
        {
            switch (node)
            {
                case SpecNode spec:
                    return spec;
                case JsonNode json:
                    return FromJson(MiniJson.ToPlain(json));
                case string s:
                    return new SpecNode(s);
                case IList list:
                    if (list.Count == 0 || !(list[0] is string head)) throw new SpecFormatException(SpecFormatException.NeedsWordMessage);
                    return new SpecNode(head, list.Cast<object>().Skip(1).Select(FromJson));
                case IDictionary<string, object> obj:
                    obj.TryGetValue("word", out var wordValue);
                    obj.TryGetValue("children", out var children);
                    bool noChildren = !MiniJson.IsTruthy(children);
                    if (wordValue is string word && (noChildren || children is IList))
                        return new SpecNode(word, noChildren ? null : ((IList)children).Cast<object>().Select(FromJson));
                    throw new SpecFormatException(SpecFormatException.BadStructureMessage);
                default:
                    throw new SpecFormatException(SpecFormatException.BadStructureMessage);
            }
        }

        /// <summary>
        /// core.js <c>canonical(tree)</c>: <c>JSON.stringify</c> of <c>[word, ...sortedChildren]</c>, children sorted by their own
        /// serialized form (UTF-16 ordinal). Two trees mean the same sentence exactly when their canonical strings are equal.
        /// </summary>
        public string Canonical()
        {
            var sb = new StringBuilder();
            sb.Append('[');
            MiniJson.AppendQuoted(sb, Word);
            if (Children.Count > 0)
            {
                var parts = Children.Select(c => c.Canonical()).ToList();
                parts.Sort(StringComparer.Ordinal); // equal strings are identical, so sort stability does not matter
                foreach (var p in parts) sb.Append(',').Append(p);
            }
            sb.Append(']');
            return sb.ToString();
        }

        /// <summary>Spec JSON in array form, children in their given order.</summary>
        public string ToSpecJson()
        {
            var sb = new StringBuilder();
            sb.Append('[');
            MiniJson.AppendQuoted(sb, Word);
            foreach (var c in Children) sb.Append(',').Append(c.ToSpecJson());
            sb.Append(']');
            return sb.ToString();
        }

        /// <inheritdoc/>
        public override string ToString() => Canonical();
    }
}
