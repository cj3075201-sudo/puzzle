using System;
using System.Collections.Generic;
using System.Linq;
using OUAT.Jigsaw;
using UnityEngine;

namespace OUAT.Core
{
    /// <summary>{"all":[...],"any":[...],"none":[...]} 깃발 조건. 비어 있으면 항상 참.</summary>
    public sealed class Condition
    {
        public List<string> All = new List<string>(), Any = new List<string>(), None = new List<string>();
        public bool Eval(GameState s) =>
            All.All(s.Has) && (Any.Count == 0 || Any.Any(s.Has)) && !None.Any(s.Has);

        public static Condition From(object o)
        {
            var c = new Condition();
            if (o is Dictionary<string, object> d)
            {
                c.All = J.Strings(d, "all"); c.Any = J.Strings(d, "any"); c.None = J.Strings(d, "none");
            }
            else if (o is List<object> l) c.All = l.Select(x => x?.ToString()).ToList();
            else if (o is string s) c.All.Add(s);
            return c;
        }
    }

    public sealed class WordDef { public string Id, Color, Note; public List<string> Accept = new List<string>(); }
    public sealed class PlaceDef { public string Id, Name, GoalName; public Dictionary<string, object> Raw; }
    public sealed class NpcDef { public string Id, Name, Model, Home; public bool Talkable; public Dictionary<string, object> Raw; }

    public sealed class ResponseDef
    {
        public SpecNode Spec; public bool Progress; public string React, Say; public List<string> Set = new List<string>();
        public Dictionary<string, object> Raw;
    }

    public sealed class DialogueDef
    {
        public string Id, Npc, Place, Their;
        public Condition OpensWhen;
        public List<string> Models = new List<string>(), Words = new List<string>();
        public int BoardW = 5, BoardH = 3;
        public List<ResponseDef> Responses = new List<ResponseDef>();
        public ResponseDef Default;
        public Dictionary<string, object> Raw;
    }

    public sealed class InscriptionDef
    {
        public string Id, Place, Sentence, Kind, Label, Picture; public List<string> Lines = new List<string>();
        public Vector2 Pos; public bool Confirms = true; public Dictionary<string, object> Raw;
        public bool IsDisplay => Kind == "display";
    }
    public sealed class OverheadDef { public string Npc, Sentence; public Condition When; }
    public sealed class PlayLine { public string Sentence, Stage; public Dictionary<string, object> Raw; }
    public sealed class PlayDef { public string Id; public List<PlayLine> Lines = new List<PlayLine>(); public Dictionary<string, object> Raw; }
    public sealed class PuzzleDef { public string Id, Type, Place, Needs; public List<string> Set = new List<string>(); public Dictionary<string, object> Raw; }
    public sealed class GoalDef { public Condition When; public string Text, Place, Hint; public Dictionary<string, object> Raw; }
    public sealed class EventDef { public string Id, On; public Condition When; public List<List<object>> Do = new List<List<object>>(); public bool Once = true; }
    public sealed class ZoneDef { public string Id, Place; public Vector2 Pos; public float Radius = 1.5f; public Dictionary<string, object> Raw; }
    public sealed class PropDef { public string Id, Place, Initial; public Vector2 Pos; public List<string> States = new List<string>(); public Dictionary<string, object> Raw; }
    public sealed class ReadableDef { public string Id, Label, Place, Text, Picture; public Vector2 Pos; public Condition VisibleWhen; public Dictionary<string, object> Raw; }
    public sealed class AreaExit { public string To, Label; public Vector2 Pos, Spawn; public float Radius = 1.6f, Face; }
    public sealed class AreaShape { public Vector2 C; public float R; public List<Vector2> Line; public float W; }
    public sealed class AreaDef
    {
        public string Id, Name; public List<string> Places = new List<string>();
        public List<AreaShape> Shapes = new List<AreaShape>(); public Rect Bounds; public Dictionary<string, object> Camera;
        public List<AreaExit> Exits = new List<AreaExit>();
        public Dictionary<string, object> Raw;

        /// <summary>점이 이 구역 모양 안쪽으로 얼마나 들어와 있나(음수 = 안).</summary>
        public float SignedDistance(Vector2 p)
        {
            float best = float.MaxValue;
            foreach (var s in Shapes)
            {
                float d;
                if (s.Line != null && s.Line.Count > 1)
                {
                    d = float.MaxValue;
                    for (int i = 0; i < s.Line.Count - 1; i++)
                    {
                        var a = s.Line[i]; var b = s.Line[i + 1]; var ab = b - a;
                        float t = Mathf.Clamp01(Vector2.Dot(p - a, ab) / Mathf.Max(1e-4f, ab.sqrMagnitude));
                        d = Mathf.Min(d, Vector2.Distance(p, a + ab * t));
                    }
                    d -= s.W;
                }
                else d = Vector2.Distance(p, s.C) - s.R;
                best = Mathf.Min(best, d);
            }
            return best;
        }
    }

    public sealed class PhaseNpc { public object At; public string Pose; public Condition When; }
    public sealed class PhaseDef { public string Id; public Condition When; public Dictionary<string, PhaseNpc> Npcs = new Dictionary<string, PhaseNpc>(); }

    /// <summary>chapter1.json 전체. 형식은 docs/설계_뼈대.md §4.</summary>
    public sealed class ChapterData
    {
        public Dictionary<string, WordDef> Words = new Dictionary<string, WordDef>();
        public Dictionary<string, PlaceDef> Places = new Dictionary<string, PlaceDef>();
        public Dictionary<string, NpcDef> Npcs = new Dictionary<string, NpcDef>();
        public Dictionary<string, SpecNode> Sentences = new Dictionary<string, SpecNode>();
        public Dictionary<string, InscriptionDef> Inscriptions = new Dictionary<string, InscriptionDef>();
        public Dictionary<string, DialogueDef> Dialogues = new Dictionary<string, DialogueDef>();
        public List<OverheadDef> Overheads = new List<OverheadDef>();
        public Dictionary<string, PlayDef> Plays = new Dictionary<string, PlayDef>();
        public Dictionary<string, PuzzleDef> Puzzles = new Dictionary<string, PuzzleDef>();
        public List<GoalDef> Goals = new List<GoalDef>();
        public List<EventDef> Events = new List<EventDef>();
        public Dictionary<string, ZoneDef> Zones = new Dictionary<string, ZoneDef>();
        public Dictionary<string, PropDef> Props = new Dictionary<string, PropDef>();
        public Dictionary<string, ReadableDef> Readables = new Dictionary<string, ReadableDef>();
        public List<PhaseDef> Phases = new List<PhaseDef>();
        public Dictionary<string, string> Translations = new Dictionary<string, string>();
        public string VillageName = "";
        public Dictionary<string, AreaDef> Areas = new Dictionary<string, AreaDef>();
        /// <summary>scenes[] 원본(id → 항목). cinematic 등 장면 설정.</summary>
        public Dictionary<string, Dictionary<string, object>> Scenes = new Dictionary<string, Dictionary<string, object>>();
        /// <summary>exitLocks[] 원본 — 조건이 참이면 그 출구로 못 넘어감.</summary>
        public List<Dictionary<string, object>> ExitLocks = new List<Dictionary<string, object>>();
        public Dictionary<string, object> Root;

        public HashSet<string> BlueWords => new HashSet<string>(Words.Values.Where(w => w.Color == "blue").Select(w => w.Id));

        public static ChapterData Parse(string json)
        {
            var root = MiniJson.Parse(json) as Dictionary<string, object>
                       ?? throw new FormatException("chapter1.json 최상위가 객체가 아님");
            var c = new ChapterData { Root = root };

            foreach (var o in J.List(root, "words"))
            {
                var d = (Dictionary<string, object>)o;
                var w = new WordDef { Id = J.Str(d, "id"), Color = J.Str(d, "color", "yellow"), Note = J.Str(d, "note"), Accept = J.Strings(d, "accept") };
                if (!w.Accept.Contains(w.Id)) w.Accept.Insert(0, w.Id);
                c.Words[w.Id] = w;
            }
            foreach (var o in J.List(root, "places"))
            {
                var d = (Dictionary<string, object>)o;
                c.Places[J.Str(d, "id")] = new PlaceDef { Id = J.Str(d, "id"), Name = J.Str(d, "name"), GoalName = J.Str(d, "goalName", J.Str(d, "name")), Raw = d };
            }
            foreach (var o in J.List(root, "npcs"))
            {
                var d = (Dictionary<string, object>)o;
                c.Npcs[J.Str(d, "id")] = new NpcDef { Id = J.Str(d, "id"), Name = J.Str(d, "name"), Model = J.Str(d, "model"), Home = J.Str(d, "home"), Talkable = J.Bool(d, "talkable", true), Raw = d };
            }
            if (root.TryGetValue("sentences", out var sObj) && sObj is Dictionary<string, object> sd)
                foreach (var kv in sd) c.Sentences[kv.Key] = SpecNode.FromJson(kv.Value);

            foreach (var o in J.List(root, "inscriptions"))
            {
                var d = (Dictionary<string, object>)o;
                var pos = J.List(d, "pos");
                var lines = J.Strings(d, "lines");
                c.Inscriptions[J.Str(d, "id")] = new InscriptionDef
                {
                    Id = J.Str(d, "id"), Place = J.Str(d, "place"), Sentence = J.Str(d, "sentence", lines.Count > 0 ? lines[0] : ""), Lines = lines.Count > 0 ? lines : new List<string> { J.Str(d, "sentence") },
                    Kind = J.Str(d, "kind", "carved"), Label = J.Str(d, "label", "새겨진 글자"), Picture = J.Str(d, "picture"),
                    Pos = pos.Count >= 2 ? new Vector2(J.F(pos[0]), J.F(pos[1])) : Vector2.zero,
                    Confirms = J.Bool(d, "confirms", true), Raw = d
                };
            }
            foreach (var o in J.List(root, "dialogues"))
            {
                var d = (Dictionary<string, object>)o;
                var dl = new DialogueDef
                {
                    Id = J.Str(d, "id"), Npc = J.Str(d, "npc"), Place = J.Str(d, "place"), Their = J.Str(d, "their"),
                    OpensWhen = Condition.From(d.TryGetValue("opensWhen", out var ow) ? ow : null),
                    Models = J.Strings(d, "models"), Words = J.Strings(d, "words"), Raw = d
                };
                var b = J.List(d, "board");
                if (b.Count >= 2) { dl.BoardW = (int)J.F(b[0]); dl.BoardH = (int)J.F(b[1]); }
                foreach (var r in J.List(d, "responses")) dl.Responses.Add(ParseResponse((Dictionary<string, object>)r));
                if (d.TryGetValue("default", out var def) && def is Dictionary<string, object> dd) dl.Default = ParseResponse(dd);
                c.Dialogues[dl.Id] = dl;
            }
            foreach (var o in J.List(root, "overheads"))
            {
                var d = (Dictionary<string, object>)o;
                c.Overheads.Add(new OverheadDef { Npc = J.Str(d, "npc"), Sentence = J.Str(d, "sentence"), When = Condition.From(d.TryGetValue("when", out var w) ? w : null) });
            }
            foreach (var o in J.List(root, "plays"))
            {
                var d = (Dictionary<string, object>)o;
                var p = new PlayDef { Id = J.Str(d, "id"), Raw = d };
                foreach (var l in J.List(d, "lines"))
                {
                    var ld = (Dictionary<string, object>)l;
                    p.Lines.Add(new PlayLine { Sentence = ld.TryGetValue("sentence", out var sv) && sv != null ? sv.ToString() : null, Stage = J.Str(ld, "stage"), Raw = ld });
                }
                c.Plays[p.Id] = p;
            }
            foreach (var o in J.List(root, "puzzles"))
            {
                var d = (Dictionary<string, object>)o;
                c.Puzzles[J.Str(d, "id")] = new PuzzleDef { Id = J.Str(d, "id"), Type = J.Str(d, "type"), Place = J.Str(d, "place"), Needs = J.Str(d, "needs"), Set = J.Strings(d, "set"), Raw = d };
            }
            foreach (var o in J.List(root, "goals"))
            {
                var d = (Dictionary<string, object>)o;
                c.Goals.Add(new GoalDef { When = Condition.From(d.TryGetValue("when", out var w) ? w : null), Text = J.Str(d, "text"), Place = J.Str(d, "place"), Hint = J.Str(d, "hint"), Raw = d });
            }
            foreach (var o in J.List(root, "events"))
            {
                var d = (Dictionary<string, object>)o;
                var e = new EventDef { Id = J.Str(d, "id"), On = J.Str(d, "on"), When = Condition.From(d.TryGetValue("when", out var w) ? w : null), Once = J.Bool(d, "once", false) };
                foreach (var a in J.List(d, "do")) if (a is List<object> al) e.Do.Add(al);
                c.Events.Add(e);
            }
            foreach (var o in J.List(root, "zones"))
            {
                var d = (Dictionary<string, object>)o;
                var pos = J.List(d, "pos");
                c.Zones[J.Str(d, "id")] = new ZoneDef { Id = J.Str(d, "id"), Place = J.Str(d, "place"), Pos = pos.Count >= 2 ? new Vector2(J.F(pos[0]), J.F(pos[1])) : Vector2.zero, Radius = d.TryGetValue("radius", out var r) ? J.F(r) : 1.5f, Raw = d };
            }
            foreach (var o in J.List(root, "props"))
            {
                var d = (Dictionary<string, object>)o;
                var pos = J.List(d, "pos");
                var states = J.Strings(d, "states");
                c.Props[J.Str(d, "id")] = new PropDef { Id = J.Str(d, "id"), Place = J.Str(d, "place"), Pos = pos.Count >= 2 ? new Vector2(J.F(pos[0]), J.F(pos[1])) : Vector2.zero, States = states, Initial = J.Str(d, "initial", states.Count > 0 ? states[0] : "default"), Raw = d };
            }
            foreach (var o in J.List(root, "readables"))
            {
                var d = (Dictionary<string, object>)o;
                var pos = J.List(d, "pos");
                c.Readables[J.Str(d, "id")] = new ReadableDef { Id = J.Str(d, "id"), Label = J.Str(d, "label"), Place = J.Str(d, "place"), Text = J.Str(d, "text"), Picture = J.Str(d, "picture"), Pos = pos.Count >= 2 ? new Vector2(J.F(pos[0]), J.F(pos[1])) : Vector2.zero, VisibleWhen = Condition.From(d.TryGetValue("visibleWhen", out var vw) ? vw : null), Raw = d };
            }
            foreach (var o in J.List(root, "phases"))
            {
                var d = (Dictionary<string, object>)o;
                var ph = new PhaseDef { Id = J.Str(d, "id"), When = Condition.From(d.TryGetValue("when", out var w) ? w : null) };
                if (d.TryGetValue("npcs", out var ns) && ns is Dictionary<string, object> nd)
                    foreach (var kv in nd)
                        if (kv.Value is Dictionary<string, object> pn) ph.Npcs[kv.Key] = new PhaseNpc { At = pn.TryGetValue("at", out var at) ? at : null, Pose = J.Str(pn, "pose", "stand"), When = pn.TryGetValue("when", out var pw) ? Condition.From(pw) : null };
                c.Phases.Add(ph);
            }
            if (root.TryGetValue("translations", out var tr) && tr is Dictionary<string, object> td)
                foreach (var kv in td) c.Translations[kv.Key] = kv.Value?.ToString() ?? "";
            foreach (var o in J.List(root, "scenes")) if (o is Dictionary<string, object> scd && scd.TryGetValue("id", out var sid)) c.Scenes[sid.ToString()] = scd;
            foreach (var o in J.List(root, "exitLocks")) if (o is Dictionary<string, object> el) c.ExitLocks.Add(el);
            foreach (var o in J.List(root, "areas"))
            {
                var d = (Dictionary<string, object>)o;
                var a = new AreaDef { Id = J.Str(d, "id"), Name = J.Str(d, "name"), Places = J.Strings(d, "places"), Camera = d.TryGetValue("camera", out var cam) ? cam as Dictionary<string, object> : null, Raw = d };
                foreach (var so in J.List(d, "shape").OfType<Dictionary<string, object>>())
                {
                    var s = new AreaShape();
                    var cc = J.List(so, "c"); if (cc.Count >= 2) { s.C = new Vector2(J.F(cc[0]), J.F(cc[1])); s.R = so.TryGetValue("r", out var rr) ? J.F(rr) : 5f; }
                    var ln = J.List(so, "line"); if (ln.Count > 1) { s.Line = ln.OfType<List<object>>().Select(q => new Vector2(J.F(q[0]), J.F(q[1]))).ToList(); s.W = so.TryGetValue("w", out var ww) ? J.F(ww) : 4f; }
                    a.Shapes.Add(s);
                }
                var bd = J.List(d, "bounds"); if (bd.Count >= 4) a.Bounds = Rect.MinMaxRect(J.F(bd[0]), J.F(bd[2]), J.F(bd[1]), J.F(bd[3]));
                foreach (var eo in J.List(d, "exits").OfType<Dictionary<string, object>>())
                {
                    var ps = J.List(eo, "pos"); var sp = J.List(eo, "spawn");
                    a.Exits.Add(new AreaExit { To = J.Str(eo, "to"), Label = J.Str(eo, "label"), Pos = new Vector2(J.F(ps[0]), J.F(ps[1])), Spawn = new Vector2(J.F(sp[0]), J.F(sp[1])), Radius = eo.TryGetValue("radius", out var er) ? J.F(er) : 1.6f, Face = eo.TryGetValue("face", out var ef) ? J.F(ef) : 0f });
                }
                c.Areas[a.Id] = a;
            }
            if (root.TryGetValue("village", out var vg) && vg is Dictionary<string, object> vd) c.VillageName = J.Str(vd, "name");
            return c;
        }

        static ResponseDef ParseResponse(Dictionary<string, object> d) => new ResponseDef
        {
            Spec = d.TryGetValue("spec", out var s) && s != null ? SpecNode.FromJson(s) : null,
            Progress = J.Bool(d, "progress", false), React = J.Str(d, "react"), Say = J.Str(d, "say"), Set = J.Strings(d, "set"), Raw = d
        };

        public PhaseDef CurrentPhase(GameState s) => Phases.LastOrDefault(p => p.When.Eval(s));
        public string Translate(string sentenceId) => sentenceId != null && Translations.TryGetValue(sentenceId, out var t) ? t : null;

        /// <summary>지금 상태에서 보일 목표(마지막으로 조건이 맞는 것).</summary>
        public GoalDef CurrentGoal(GameState s) => Goals.LastOrDefault(g => g.When.Eval(s));

        /// <summary>문장 속 낱말 id(중복 제거, 등장 순서).</summary>
        public static List<string> WordsOf(SpecNode n)
        {
            var list = new List<string>();
            void Walk(SpecNode x) { if (x == null) return; if (!string.IsNullOrEmpty(x.Word) && !list.Contains(x.Word)) list.Add(x.Word); foreach (var ch in x.Children) Walk(ch); }
            Walk(n);
            return list;
        }

        // ── 추측 판정: 직접 쓴 추측을 받아 줄 말 목록과 견준다(공백·문장부호·흔한 끝말 무시) ──
        public bool IsGuessCorrect(string wordId, string guess)
        {
            if (!Words.TryGetValue(wordId, out var w) || string.IsNullOrWhiteSpace(guess)) return false;
            var g = Normalize(guess);
            foreach (var a in w.Accept)
            {
                var n = Normalize(a);
                if (n == g) return true;
            }
            return false;
        }

        static string Normalize(string s)
        {
            var chars = s.Trim().ToLowerInvariant().Where(ch => !char.IsWhiteSpace(ch) && !char.IsPunctuation(ch) && !char.IsSymbol(ch));
            return new string(chars.ToArray());
        }

        static readonly string[] Endings = { "합니다", "습니다", "ㅂ니다", "어요", "아요", "해요", "요", "기", "음", "다", "는", "은", "을", "를", "의", "에", "로" };
        static string Stem(string s)
        {
            foreach (var e in Endings)
                if (s.Length > e.Length + 0 && s.EndsWith(e, StringComparison.Ordinal)) return s.Substring(0, s.Length - e.Length);
            return s;
        }
    }

    /// <summary>MiniJson 결과(Dictionary/List/string/double/bool) 읽기 도우미.</summary>
    public static class J
    {
        public static string Str(Dictionary<string, object> d, string k, string def = "") => d != null && d.TryGetValue(k, out var v) && v != null ? v.ToString() : def;
        public static bool Bool(Dictionary<string, object> d, string k, bool def) => d != null && d.TryGetValue(k, out var v) && v is bool b ? b : def;
        public static float F(object o) => o is double dd ? (float)dd : o is long l ? l : o is int i ? i : float.TryParse(o?.ToString(), out var f) ? f : 0f;
        public static List<object> List(Dictionary<string, object> d, string k) => d != null && d.TryGetValue(k, out var v) && v is List<object> l ? l : new List<object>();
        public static List<string> Strings(Dictionary<string, object> d, string k) => List(d, k).Select(x => x?.ToString()).Where(x => x != null).ToList();
    }
}
