using System;
using System.Collections;
using System.Collections.Generic;
using System.Linq;
using OUAT.Core;
using OUAT.Jigsaw;
using UnityEngine;
using UnityEngine.UIElements;

namespace OUAT.UI
{
    /// <summary>
    /// 대화창 = 탁자 위에 펼친 공책(화-02). 왼쪽 쪽: 상대 이름, 상대의 말(이미 조립된 읽기 판, 직-24)과 대답, 이번 대화에 꺼내 준 모형·글자 쟁반.
    /// 오른쪽 쪽: 연필로 그은 조립판(내 말), 「말하기」.
    /// 모형을 끌어 칸에 놓고(놓일 자리 미리보기) → 글자를 끌어 조각에 넣고(빈 모형에 그 글자 색이 입혀짐, 직-22) → 「말하기」.
    /// 조각을 놓을 때마다 이음새 모양이 맞는지만 표시한다(잉크 땀 = 맞물림, 붉은 X = 안 맞물림). 뜻은 말하기 전에 판정하지 않는다.
    /// 말하면 공책이 아래로 내려가 상대의 몸짓(세계)을 보여 준 뒤 돌아온다. 그만두고 나가도 그 대화의 판은 남는다.
    /// 처음 열 때는 세 걸음 안내(깃발 tut_board).
    /// </summary>
    public class DialogueScreen : VisualElement
    {
        readonly UIRoot ui;
        DialogueDef def;
        Action<DialogueDef, bool> onClose;
        int boardW, boardH; float cell;
        readonly VisualElement spread, theirRow, theirNote, replyNote, palette, chips, board, boardGrid, jointLayer, dragLayer, tutLayer, tutNote, tutArrow, tutCircle, speakBtn;
        readonly Label npcName, title, feedback, tutText, tutNum;
        readonly List<PieceView> placed = new List<PieceView>();
        ReadBoard theirBoard, replyBoard;
        int idSeq;
        bool resolving;
        public bool Peeking { get; private set; }

        // 끌기 상태
        enum DragKind { None, NewPiece, MovePiece, Word }
        DragKind drag; string dragModel, dragWord; PieceView dragPiece, dragGhost, snapGhost, wordTarget; VisualElement dragChip;
        Vector2 grabOffset, downPos; bool dragMoved; int dragPointer = -1; VisualElement downSource;
        Vector2Int? snapCell;

        struct JointMark { public Vector2 pos; public bool ok, acrossX, ghost; }
        readonly List<JointMark> joints = new List<JointMark>();

        struct SavedPiece { public string model, word; public int x, y; }
        static readonly Dictionary<string, List<SavedPiece>> savedBoards = new Dictionary<string, List<SavedPiece>>();

        int tutStep;
        VisualElement gestureNote;
        string gestureKind;

        static readonly Color Pencil = new Color(0.33f, 0.30f, 0.27f, 1f);

        public DialogueScreen(UIRoot ui)
        {
            this.ui = ui;
            AddToClassList("screen"); AddToClassList("dialogue-screen");
            style.display = DisplayStyle.None;
            pickingMode = PickingMode.Position;
            Add(UIKit.Box("vignette"));

            spread = UIKit.Box("dlg-spread");
            Add(spread);

            // ── 왼쪽 쪽: 상대 ──
            var left = UIKit.Box("dlg-left"); spread.Add(left);
            var head = UIKit.Box("dlg-head"); left.Add(head);
            npcName = UIKit.Text("", "dlg-name", Face.SerifBold); head.Add(npcName);
            head.Add(UIKit.Box("dlg-name-line"));
            title = UIKit.Text("", "dlg-title", Face.Serif); head.Add(title);
            title.style.display = DisplayStyle.None;   // 화-13: 할 일 문구(대화 제목)는 화면에 내지 않는다
            // 가르치는 몸짓 쪽지(ShowGestureHint) — 이름 오른쪽에 테이프로
            gestureNote = UIKit.Box("gesture-note");
            UIKit.Rotate(gestureNote, 2.2f);
            gestureNote.style.display = DisplayStyle.None;
            left.Add(gestureNote);

            theirRow = UIKit.Box("dlg-their-row"); left.Add(theirRow);
            theirNote = UIKit.Box("their-note"); theirRow.Add(theirNote);
            UIKit.Rotate(theirNote, -1.3f);
            replyNote = UIKit.Box("reply-note"); theirRow.Add(replyNote);
            UIKit.Rotate(replyNote, 1.6f);
            replyNote.style.display = DisplayStyle.None;

            var modelTray = UIKit.Box("tray model-tray"); left.Add(modelTray);
            modelTray.Add(Tag("모형"));
            palette = UIKit.Box("palette"); modelTray.Add(palette);
            var chipTray = UIKit.Box("tray chip-tray"); left.Add(chipTray);
            chipTray.Add(Tag("글자"));
            chips = UIKit.Box("chips"); chipTray.Add(chips);

            // ── 오른쪽 쪽: 내 말 ──
            var right = UIKit.Box("dlg-right"); spread.Add(right);
            right.Add(UIKit.Text("내 말", "board-label", Face.Hand));
            var boardWrap = UIKit.Box("board-wrap"); right.Add(boardWrap);
            board = UIKit.Box("board"); boardWrap.Add(board);
            boardGrid = UIKit.Box("board-grid"); board.Add(boardGrid);
            boardGrid.generateVisualContent += DrawGrid;
            jointLayer = UIKit.Box("joint-layer"); board.Add(jointLayer);
            jointLayer.generateVisualContent += DrawJoints;
            feedback = UIKit.Text("", "dlg-feedback", Face.Hand); boardWrap.Add(feedback);

            var bottom = UIKit.Box("dlg-bottom"); right.Add(bottom);
            bottom.Add(UIKit.InkButton("다시 쓰기", ClearBoard));
            bottom.Add(UIKit.InkButton("그만두기", () => Close(false)));
            speakBtn = UIKit.BrushButton("말하기", Speak, red: true, extra: "speak-btn");
            right.Add(speakBtn);

            // ── 처음 안내 ──
            tutLayer = UIKit.Box("tut-layer"); spread.Add(tutLayer);
            tutCircle = UIKit.Box("tut-circle"); tutLayer.Add(tutCircle);
            tutArrow = UIKit.Box("tut-arrow"); tutLayer.Add(tutArrow);
            tutArrow.style.transformOrigin = new TransformOrigin(Length.Percent(82.8f), Length.Percent(80.5f), 0f);
            tutNote = UIKit.Box("tut-note"); tutLayer.Add(tutNote);
            UIKit.Rotate(tutNote, -1.5f);
            tutNum = UIKit.Text("", "tut-num", Face.Hand); tutNote.Add(tutNum);
            tutText = UIKit.Text("", "tut-text", Face.Hand); tutNote.Add(tutText);
            tutNote.Add(UIKit.Box("tape tape-top"));
            tutLayer.style.display = DisplayStyle.None;
            tutLayer.schedule.Execute(PlaceTutorial).Every(90);

            dragLayer = UIKit.Box("drag-layer"); Add(dragLayer);

            RegisterCallback<PointerMoveEvent>(OnMove);
            RegisterCallback<PointerUpEvent>(OnUp);
        }

        static VisualElement Tag(string text)
        {
            var t = UIKit.Box("tray-tag");
            t.Add(UIKit.Text(text, "tray-tag-text", Face.Hand));
            return t;
        }

        public bool IsOpen => style.display == DisplayStyle.Flex;

        public void Open(DialogueDef d, Action<DialogueDef, bool> closed)
        {
            def = d; onClose = closed; resolving = false;
            SetPeek(false);
            var tune = GameTuning.Get();
            boardW = tune.boardWidthOverride > 0 ? tune.boardWidthOverride : (d.BoardW > 0 ? d.BoardW : tune.defaultBoard.x);
            boardH = tune.boardHeightOverride > 0 ? tune.boardHeightOverride : (d.BoardH > 0 ? d.BoardH : tune.defaultBoard.y);
            cell = tune.cellSize;
            var g = Game.I;
            npcName.text = g.Data.Npcs.TryGetValue(d.Npc, out var n) ? n.Name : d.Npc;
            title.text = J.Str(d.Raw, "title");
            ShowNote("");

            foreach (var p in placed) p.RemoveFromHierarchy();
            placed.Clear();
            joints.Clear(); snapCell = null;
            board.style.width = boardW * cell; board.style.height = boardH * cell;
            boardGrid.style.width = boardW * cell; boardGrid.style.height = boardH * cell;
            jointLayer.style.width = boardW * cell; jointLayer.style.height = boardH * cell;
            boardGrid.MarkDirtyRepaint(); jointLayer.MarkDirtyRepaint();

            theirNote.Clear(); replyNote.Clear(); replyNote.style.display = DisplayStyle.None; replyBoard = null;
            theirNote.Add(UIKit.Box("tape tape-top"));
            theirNote.Add(UIKit.Text("들은 말", "note-label", Face.Hand));
            if (!string.IsNullOrEmpty(d.Their) && g.Data.Sentences.TryGetValue(d.Their, out var spec))
            {
                theirBoard = new ReadBoard(spec, cell * tune.readBoardScale) { GlyphClicked = (w, el) => ui.EditGuess(w, el, RefreshGuesses) };
                theirNote.Add(theirBoard);
                foreach (var w in ChapterData.WordsOf(spec)) g.State.See(w, d.Place);   // 지금 본 말 → 칩으로 바로 쓸 수 있게
                UIRoot.NoteSeen(d.Their, null, d.Place);
            }
            else { theirBoard = null; theirNote.Add(UIKit.Text("말없이 이쪽을 본다", "their-empty", Face.Hand)); }

            BuildPalette(d, tune);
            BuildChips(d);
            if (savedBoards.TryGetValue(d.Id, out var saved))
                foreach (var s in saved)
                    if (g.Models.Models.ContainsKey(s.model) && s.x < boardW && s.y < boardH && !placed.Any(p => p.CellX == s.x && p.CellY == s.y))
                        AddPiece(s.model, s.x, s.y, s.word);
            RecomputeJoints();
            UIKit.SetEnabledLook(speakBtn, true);
            style.display = DisplayStyle.Flex;
            UIKit.AnimateIn(spread, "dlg-start", 20);
            tutStep = g.State.Has("tut_board") ? 0 : 1;
            CheckTutorial();
            ApplyGesture(false);
            AudioHub.Play("page", 0.5f);
        }

        void BuildPalette(DialogueDef d, GameTuning tune)
        {
            palette.Clear();
            var g = Game.I;
            var ids = d.Models.Where(m => g.Models.Models.ContainsKey(m)).ToList();
            if (tune.extraModels > 0)
                foreach (var m in g.Models.InOrder.Select(x => x.Id).Where(x => !ids.Contains(x) && g.Models.Models[x].IsUsable).Take(tune.extraModels)) ids.Add(m);
            if (ids.Count == 0) ids = g.Models.InOrder.Where(m => m.IsUsable).Take(6).Select(m => m.Id).ToList();
            float pc = PaletteCell;
            foreach (var id in ids)
            {
                var slot = UIKit.Box("tray-slot", PickingMode.Position);
                slot.style.width = pc * 1.5f; slot.style.height = pc * 1.5f;
                UIKit.Rotate(slot, UIKit.Jitter(id, 3f));
                var v = new PieceView(g.Models.Models[id], pc) { pickingMode = PickingMode.Ignore };
                v.style.left = pc * 0.25f; v.style.top = pc * 0.25f;
                slot.Add(v);
                var modelId = id;
                slot.RegisterCallback<PointerDownEvent>(e => BeginDrag(e, DragKind.NewPiece, modelId, null, null, slot, v));
                palette.Add(slot);
            }
        }

        float PaletteCell => cell * 0.56f;

        void BuildChips(DialogueDef d)
        {
            chips.Clear();
            var g = Game.I;
            foreach (var w in d.Words)
            {
                if (!g.State.Word(w).seen) continue;   // 본 적 있는 글자만 꺼내 준다(QA P2-13)
                var chip = UIKit.Box("chip " + (JigsawCore.ColorOf(w, g.Blue) == "blue" ? "chip-blue" : "chip-yellow"), PickingMode.Position);
                UIKit.Rotate(chip, UIKit.Jitter(d.Id + w, 3.5f));
                chip.Add(UIKit.Picture(PieceView.GlyphTexture(w), "chip-glyph"));
                chip.Add(UIKit.Text("", "chip-guess", Face.Hand));
                chip.Add(UIKit.Box("chip-seal"));
                chip.Add(UIKit.Box("chip-memo"));
                chip.userData = w;
                var word = w;
                chip.RegisterCallback<PointerDownEvent>(e => BeginDrag(e, DragKind.Word, null, word, null, chip, chip));
                chips.Add(chip);
            }
            RefreshChips();
        }

        void RefreshChips()
        {
            var g = Game.I;
            foreach (var chip in chips.Children())
            {
                var w = chip.userData as string;
                var st = g.State.Word(w);
                var l = chip.Q<Label>(className: "chip-guess");
                l.text = st.confirmed || !string.IsNullOrEmpty(st.guess) ? ReadBoard.GuessOrBlank(w) : "?";
                l.EnableInClassList("chip-guess-none", !st.confirmed && string.IsNullOrEmpty(st.guess));
                chip.EnableInClassList("chip-confirmed", st.confirmed);
                chip.EnableInClassList("chip-has-memo", !string.IsNullOrEmpty(st.memo));
            }
        }

        void RefreshGuesses()
        {
            theirBoard?.RefreshGuesses();
            replyBoard?.RefreshGuesses();
            RefreshChips();
            var g = Game.I;
            foreach (var p in placed) if (p.Word != null) p.SetGuess(ReadBoard.GuessOrBlank(p.Word), g.State.Word(p.Word).confirmed);
        }

        // ── 끌기 ─────────────────────────────────────────
        void BeginDrag(PointerDownEvent e, DragKind kind, string model, string word, PieceView piece, VisualElement source, VisualElement offsetFrom)
        {
            if (resolving || Peeking) return;
            if (e.button == 1 && piece != null) { RemovePiece(piece); RecomputeJoints(); e.StopPropagation(); return; }
            if (e.button != 0) return;
            drag = kind; dragModel = model; dragWord = word; dragPiece = piece; dragMoved = false;
            downPos = e.position; dragPointer = e.pointerId; downSource = source;
            grabOffset = offsetFrom.WorldToLocal(e.position);
            if (kind == DragKind.NewPiece) grabOffset = new Vector2(Mathf.Clamp(grabOffset.x, 0, PaletteCell), Mathf.Clamp(grabOffset.y, 0, PaletteCell));
            this.CapturePointer(e.pointerId);
            e.StopPropagation();
        }

        void StartVisual()
        {
            var g = Game.I;
            if (drag == DragKind.NewPiece || drag == DragKind.MovePiece)
            {
                var model = drag == DragKind.NewPiece ? g.Models.Models[dragModel] : dragPiece.Model;
                dragGhost = new PieceView(model, cell) { pickingMode = PickingMode.Ignore };
                dragGhost.AddToClassList("drag-piece");
                if (drag == DragKind.MovePiece)
                {
                    dragGhost.SetWord(dragPiece.Word, dragPiece.ColorName);
                    dragPiece.style.opacity = 0.2f;
                    grabOffset = grabOffset * (cell / dragPiece.Cell);
                }
                else grabOffset = grabOffset * (cell / PaletteCell);
                dragLayer.Add(dragGhost);
                snapGhost = new PieceView(model, cell) { Ghost = true, pickingMode = PickingMode.Ignore };
                if (drag == DragKind.MovePiece) snapGhost.SetWord(dragPiece.Word, dragPiece.ColorName);
                snapGhost.style.display = DisplayStyle.None;
                board.Add(snapGhost);
                jointLayer.BringToFront();
                AudioHub.Play("piece", 0.4f);
            }
            else if (drag == DragKind.Word)
            {
                var g2 = Game.I;
                dragChip = UIKit.Box("chip drag-chip " + (JigsawCore.ColorOf(dragWord, g2.Blue) == "blue" ? "chip-blue" : "chip-yellow"));
                dragChip.Add(UIKit.Picture(PieceView.GlyphTexture(dragWord), "chip-glyph"));
                dragLayer.Add(dragChip);
                grabOffset = new Vector2(40, 46);
                AudioHub.Play("piece", 0.3f, 1.3f);
            }
        }

        void OnMove(PointerMoveEvent e)
        {
            if (drag == DragKind.None || e.pointerId != dragPointer) return;
            if (!dragMoved && ((Vector2)e.position - downPos).sqrMagnitude > 36f) { dragMoved = true; StartVisual(); }
            if (!dragMoved) return;
            var local = dragLayer.WorldToLocal(e.position) - grabOffset;
            var el = (VisualElement)dragGhost ?? dragChip;
            if (el == null) return;
            el.style.left = local.x; el.style.top = local.y;
            if (dragGhost != null) UpdateSnap(CellUnder(e.position));
            else if (drag == DragKind.Word) UpdateWordTarget(PieceAt(e.position));
        }

        void UpdateSnap(Vector2Int? c)
        {
            if (c == snapCell) return;
            snapCell = c;
            board.EnableInClassList("board-hot", c.HasValue);
            if (snapGhost != null)
            {
                snapGhost.style.display = c.HasValue ? DisplayStyle.Flex : DisplayStyle.None;
                if (c.HasValue) { snapGhost.style.left = c.Value.x * cell; snapGhost.style.top = c.Value.y * cell; }
            }
            boardGrid.MarkDirtyRepaint();
            RecomputeJoints();
        }

        void UpdateWordTarget(PieceView t)
        {
            if (t == wordTarget) return;
            if (wordTarget != null) { wordTarget.PreviewColor = null; wordTarget.Hot = false; }
            wordTarget = t;
            if (t != null) { t.PreviewColor = JigsawCore.ColorOf(dragWord, Game.I.Blue); t.Hot = true; }
        }

        PieceView PieceAt(Vector2 panelPos) => placed.LastOrDefault(p => p.ContainsLocal(p.WorldToLocal(panelPos)));

        void OnUp(PointerUpEvent e)
        {
            if (drag == DragKind.None || e.pointerId != dragPointer) return;
            this.ReleasePointer(e.pointerId);
            board.RemoveFromClassList("board-hot");
            try
            {
                if (!dragMoved)
                {
                    // 그냥 누름: 글자 칩 → 추측 쓰기
                    if (drag == DragKind.Word) ui.EditGuess(dragWord, downSource, RefreshGuesses);
                    return;
                }
                var g = Game.I;
                if (drag == DragKind.NewPiece || drag == DragKind.MovePiece)
                {
                    var c = CellUnder(e.position);
                    if (c.HasValue)
                    {
                        var occupant = placed.FirstOrDefault(p => p.CellX == c.Value.x && p.CellY == c.Value.y && p != dragPiece);
                        if (drag == DragKind.NewPiece)
                        {
                            int limit = GameTuning.Get().pieceLimit;
                            if (limit > 0 && placed.Count >= limit && occupant == null) { ShowNote("조각을 더 놓을 수 없다"); UIKit.Shake(downSource); return; }
                            if (occupant != null) RemovePiece(occupant, quiet: true);
                            AddPiece(dragModel, c.Value.x, c.Value.y, null);
                        }
                        else
                        {
                            if (occupant != null) { occupant.CellX = dragPiece.CellX; occupant.CellY = dragPiece.CellY; Place(occupant); }
                            dragPiece.CellX = c.Value.x; dragPiece.CellY = c.Value.y; Place(dragPiece);
                        }
                        AudioHub.Play("drop", 0.6f);
                    }
                    else if (drag == DragKind.MovePiece) RemovePiece(dragPiece);
                    else { UIKit.Shake(downSource); AudioHub.Play("piece", 0.3f, 0.7f); }
                }
                else if (drag == DragKind.Word)
                {
                    var target = PieceAt(e.position);
                    if (target != null)
                    {
                        target.SetWord(dragWord, JigsawCore.ColorOf(dragWord, g.Blue));
                        target.SetGuess(ReadBoard.GuessOrBlank(dragWord), g.State.Word(dragWord).confirmed);
                        AudioHub.Play("piece", 0.7f, 1.2f);
                        ShowNote("");
                    }
                    else { UIKit.Shake(downSource); AudioHub.Play("piece", 0.3f, 0.7f); }
                }
            }
            finally
            {
                if (dragPiece != null) dragPiece.style.opacity = 1f;
                dragGhost?.RemoveFromHierarchy(); dragChip?.RemoveFromHierarchy(); snapGhost?.RemoveFromHierarchy();
                if (wordTarget != null) { wordTarget.PreviewColor = null; wordTarget.Hot = false; }
                dragGhost = null; dragChip = null; snapGhost = null; wordTarget = null; snapCell = null;
                drag = DragKind.None; dragPiece = null; dragPointer = -1;
                boardGrid.MarkDirtyRepaint();
                RecomputeJoints();
                CheckTutorial();
            }
        }

        Vector2Int? CellUnder(Vector2 panelPos)
        {
            // 조각 왼쪽 위 모서리 기준으로 칸을 정한다(잡은 자리 보정)
            var local = board.WorldToLocal(panelPos) - grabOffset + new Vector2(cell / 2f, cell / 2f);
            int x = Mathf.FloorToInt(local.x / cell), y = Mathf.FloorToInt(local.y / cell);
            if (x < 0 || y < 0 || x >= boardW || y >= boardH) return null;
            return new Vector2Int(x, y);
        }

        PieceView AddPiece(string modelId, int x, int y, string word)
        {
            var g = Game.I;
            var v = new PieceView(g.Models.Models[modelId], cell) { PieceId = "p" + (++idSeq), CellX = x, CellY = y };
            v.SetWord(word, word == null ? "none" : JigsawCore.ColorOf(word, g.Blue));
            if (word != null) v.SetGuess(ReadBoard.GuessOrBlank(word), g.State.Word(word).confirmed);
            v.RegisterCallback<PointerDownEvent>(e => BeginDrag(e, DragKind.MovePiece, null, null, v, v, v));
            v.RegisterCallback<ClickEvent>(e => { if (e.clickCount == 2 && v.Word != null && !resolving) { v.SetWord(null, "none"); AudioHub.Play("piece", 0.4f, 0.8f); RecomputeJoints(); } });
            board.Add(v); placed.Add(v);
            jointLayer.BringToFront();
            Place(v);
            return v;
        }

        void Place(PieceView v) { v.style.left = v.CellX * cell; v.style.top = v.CellY * cell; }

        void RemovePiece(PieceView v, bool quiet = false)
        {
            placed.Remove(v); v.RemoveFromHierarchy();
            if (!quiet) AudioHub.Play("piece", 0.35f, 0.7f);
        }

        void ClearBoard()
        {
            if (resolving) return;
            foreach (var p in placed.ToList()) RemovePiece(p, true);
            ShowNote("");
            RecomputeJoints();
            AudioHub.Play("page", 0.4f);
        }

        // ── 이음새 모양 표시(뜻 판정 아님) ─────────────────
        void RecomputeJoints()
        {
            joints.Clear();
            var cells = new Dictionary<(int, int), (JigsawModel m, bool ghost)>();
            bool pieceDrag = (drag == DragKind.NewPiece || drag == DragKind.MovePiece) && dragMoved;
            foreach (var p in placed)
            {
                if (pieceDrag && drag == DragKind.MovePiece && p == dragPiece && snapCell.HasValue) continue;
                cells[(p.CellX, p.CellY)] = (p.Model, false);
            }
            if (pieceDrag && snapCell.HasValue)
            {
                var g = Game.I;
                var model = drag == DragKind.NewPiece ? g.Models.Models[dragModel] : dragPiece.Model;
                var key = (snapCell.Value.x, snapCell.Value.y);
                if (drag == DragKind.MovePiece && cells.TryGetValue(key, out var occ) && !(dragPiece.CellX == key.Item1 && dragPiece.CellY == key.Item2))
                    cells[(dragPiece.CellX, dragPiece.CellY)] = (occ.m, false);
                cells[key] = (model, true);
            }
            foreach (var kv in cells)
            {
                foreach (var side in new[] { Side.E, Side.S })
                {
                    var nk = (kv.Key.Item1 + side.Dx(), kv.Key.Item2 + side.Dy());
                    if (!cells.TryGetValue(nk, out var nb)) continue;
                    bool ha = kv.Value.m.TryGetPort(side, out var pa);
                    bool hb = nb.m.TryGetPort(side.Opposite(), out var pb);
                    if (!ha && !hb) continue;
                    bool ok = ha && hb && pa.Fits(pb);
                    var pos = side == Side.E ? new Vector2((kv.Key.Item1 + 1) * cell, (kv.Key.Item2 + 0.5f) * cell)
                                             : new Vector2((kv.Key.Item1 + 0.5f) * cell, (kv.Key.Item2 + 1) * cell);
                    joints.Add(new JointMark { pos = pos, ok = ok, acrossX = side == Side.E, ghost = kv.Value.ghost || nb.ghost });
                }
            }
            jointLayer.MarkDirtyRepaint();
        }

        void DrawJoints(MeshGenerationContext ctx)
        {
            var p = ctx.painter2D;
            p.lineCap = LineCap.Round;
            foreach (var j in joints)
            {
                float a = j.ghost ? 0.65f : 1f;
                if (j.ok)
                {
                    // 잉크 땀 두 줄(이음새를 가로지름)
                    p.strokeColor = new Color(PieceView.Ink.r, PieceView.Ink.g, PieceView.Ink.b, 0.85f * a);
                    p.lineWidth = 3f;
                    for (int k = -1; k <= 1; k += 2)
                    {
                        Vector2 along = j.acrossX ? new Vector2(0, k * 6f) : new Vector2(k * 6f, 0);
                        Vector2 across = j.acrossX ? new Vector2(8f, 1f) : new Vector2(1f, 8f);
                        p.BeginPath(); p.MoveTo(j.pos + along - across); p.LineTo(j.pos + along + across); p.Stroke();
                    }
                }
                else
                {
                    var red = new Color(PieceView.Seal.r, PieceView.Seal.g, PieceView.Seal.b, a);
                    p.strokeColor = new Color(red.r, red.g, red.b, 0.35f * a);
                    p.lineWidth = 1.6f;
                    p.BeginPath(); p.Arc(j.pos, 14f, 0, 340); p.Stroke();
                    p.strokeColor = red;
                    p.lineWidth = 3.4f;
                    p.BeginPath(); p.MoveTo(j.pos + new Vector2(-7, -8)); p.LineTo(j.pos + new Vector2(7, 7)); p.Stroke();
                    p.BeginPath(); p.MoveTo(j.pos + new Vector2(7, -7)); p.LineTo(j.pos + new Vector2(-6, 8)); p.Stroke();
                }
            }
        }

        // ── 연필 조립판 ───────────────────────────────────
        void DrawGrid(MeshGenerationContext ctx)
        {
            var p = ctx.painter2D;
            float w = boardW * cell, h = boardH * cell;
            p.lineCap = LineCap.Round;
            // 놓일 칸 연필 칠
            if (snapCell.HasValue)
            {
                p.fillColor = new Color(Pencil.r, Pencil.g, Pencil.b, 0.08f);
                var c = snapCell.Value;
                p.BeginPath();
                p.MoveTo(new Vector2(c.x * cell + 3, c.y * cell + 3)); p.LineTo(new Vector2((c.x + 1) * cell - 3, c.y * cell + 3));
                p.LineTo(new Vector2((c.x + 1) * cell - 3, (c.y + 1) * cell - 3)); p.LineTo(new Vector2(c.x * cell + 3, (c.y + 1) * cell - 3));
                p.ClosePath(); p.Fill();
            }
            // 칸 안쪽 연필 선(옅게, 칸마다 살짝 다르게 그어 손맛)
            p.strokeColor = new Color(Pencil.r, Pencil.g, Pencil.b, 0.16f);
            p.lineWidth = 1.2f;
            for (int x = 1; x < boardW; x++) Wobbly(p, new Vector2(x * cell, 4), new Vector2(x * cell, h - 4), x * 7);
            for (int y = 1; y < boardH; y++) Wobbly(p, new Vector2(4, y * cell), new Vector2(w - 4, y * cell), y * 13 + 3);
            // 바깥 테두리: 모서리에서 조금 넘치는 밑그림 선
            p.strokeColor = new Color(Pencil.r, Pencil.g, Pencil.b, 0.55f);
            p.lineWidth = 1.8f;
            Wobbly(p, new Vector2(-12, 0), new Vector2(w + 9, 0), 101);
            Wobbly(p, new Vector2(-8, h), new Vector2(w + 12, h), 102);
            Wobbly(p, new Vector2(0, -11), new Vector2(0, h + 8), 103);
            Wobbly(p, new Vector2(w, -8), new Vector2(w, h + 12), 104);
            // 칸 꼭짓점 연필 점
            p.fillColor = new Color(Pencil.r, Pencil.g, Pencil.b, 0.35f);
            for (int y = 0; y <= boardH; y++)
                for (int x = 0; x <= boardW; x++) { p.BeginPath(); p.Arc(new Vector2(x * cell, y * cell), 2.2f, 0, 360); p.Fill(); }
        }

        static void Wobbly(Painter2D p, Vector2 a, Vector2 b, int seed)
        {
            var dir = b - a; var n = new Vector2(-dir.y, dir.x).normalized;
            float k1 = Mathf.Sin(seed * 12.9898f) * 1.6f, k2 = Mathf.Sin(seed * 78.233f) * 1.4f;
            p.BeginPath(); p.MoveTo(a);
            p.BezierCurveTo(a + dir * 0.33f + n * k1, a + dir * 0.66f + n * k2, b);
            p.Stroke();
        }

        // ── 말하기 ───────────────────────────────────────
        void Speak()
        {
            if (resolving || Peeking) return;
            var g = Game.I;
            if (placed.Count == 0) { ShowNote("판에 아무것도 없다"); UIKit.Shake(board, 6f); return; }
            if (tutStep > 0) FinishTutorial();
            var pieces = placed.Select(p => new Piece(p.PieceId, p.Model.Id, p.Word ?? "", p.CellX, p.CellY)).ToList();
            var res = JigsawCore.Analyze(pieces, g.Models, g.Blue, new AnalyzeOptions { BoardWidth = boardW, BoardHeight = boardH });
            if (!res.Ok)
            {
                ShowNote(CodeHint(res.Code));
                UIKit.Shake(board, 6f);
                AudioHub.Play("wrong", 0.3f);
                ui.StartCoroutine(g.director.React(def.Npc, "tilt"));
                return;
            }
            var canon = res.Canonical;
            var match = def.Responses.FirstOrDefault(r => r.Spec != null && r.Spec.Canonical() == canon);
            var used = ChapterData.WordsOf(res.Tree);
            ui.StartCoroutine(Resolve(match ?? def.Default, used, match != null && match.Progress));
        }

        IEnumerator Resolve(ResponseDef r, List<string> used, bool progress)
        {
            resolving = true;
            UIKit.SetEnabledLook(speakBtn, false);
            var g = Game.I;
            AudioHub.Play("speak", 0.6f);
            ShowNote("");
            foreach (var p in placed) { p.Glow = progress; p.MarkDirtyRepaint(); }
            if (r != null && !string.IsNullOrEmpty(r.Say) && g.Data.Sentences.TryGetValue(r.Say, out var say))
            {
                replyNote.Clear();
                replyNote.Add(UIKit.Box("tape tape-top"));
                replyNote.Add(UIKit.Text("대답", "note-label", Face.Hand));
                replyBoard = new ReadBoard(say, cell * 0.5f) { GlyphClicked = (w, el) => ui.EditGuess(w, el, RefreshGuesses) };
                replyNote.Add(replyBoard);
                replyNote.style.display = DisplayStyle.Flex;
                UIKit.AnimateIn(replyNote, "note-start", 30);
                UIRoot.NoteSeen(r.Say, ChapterData.WordsOf(say), def.Place);
            }
            // 공책을 내려 상대의 몸짓(세계)을 보여 준다
            yield return new WaitForSeconds(0.35f);
            SetPeek(true);
            yield return new WaitForSeconds(0.45f);
            yield return g.RunResponse(def, r, used, counted: !progress);
            if (progress)
            {
                AudioHub.Play("confirm", 0.5f);
                yield return new WaitForSeconds(0.9f);
                resolving = false;
                UIKit.SetEnabledLook(speakBtn, true);
                Close(true);
                yield break;
            }
            yield return new WaitForSeconds(0.4f);
            SetPeek(false);
            yield return new WaitForSeconds(0.35f);
            if (r == null || r == def.Default) ShowNote("통하지 않은 것 같다. 몸짓을 떠올리며 다시 짜 보자");
            foreach (var p in placed) { p.Glow = false; p.MarkDirtyRepaint(); }
            RefreshGuesses();
            resolving = false;
            UIKit.SetEnabledLook(speakBtn, true);
        }

        void SetPeek(bool on)
        {
            Peeking = on;
            EnableInClassList("dlg-peek", on);
        }

        static string CodeHint(string code)
        {
            switch (code)
            {
                case JigsawCodes.EmptyWord: return "글자를 넣지 않은 조각이 있다";
                case JigsawCodes.Disconnected: return "조각이 모두 이어져 있지 않다";
                case JigsawCodes.PortMismatch: return "맞물리지 않는 이음새가 있다 — 붉은 표시를 보자";
                case JigsawCodes.Cycle: return "이음이 고리처럼 돌아간다";
                case JigsawCodes.MultipleParents: return "한 조각으로 두 갈래가 들어온다";
                case JigsawCodes.RootCount: return "말이 시작되는 조각이 하나가 아니다";
                case JigsawCodes.ChainLimit: return "노랑 조각이 너무 길게 이어졌다";
                case JigsawCodes.BranchLimit: return "갈래가 너무 많다";
                default: return "이 모양으로는 말이 되지 않는다";
            }
        }

        void ShowNote(string s)
        {
            feedback.text = s ?? "";
            feedback.style.display = string.IsNullOrEmpty(s) ? DisplayStyle.None : DisplayStyle.Flex;
            if (!string.IsNullOrEmpty(s)) UIKit.AnimateIn(feedback, "note-start", 30);
        }

        void Close(bool success)
        {
            if (resolving) return;
            if (def != null)
            {
                if (success || placed.Count == 0) savedBoards.Remove(def.Id);
                else savedBoards[def.Id] = placed.Select(p => new SavedPiece { model = p.Model.Id, word = p.Word, x = p.CellX, y = p.CellY }).ToList();
            }
            SetPeek(false);
            tutLayer.style.display = DisplayStyle.None;
            gestureKind = null; gestureNote.style.display = DisplayStyle.None;
            style.display = DisplayStyle.None;
            var cb = onClose; onClose = null;
            cb?.Invoke(def, success);
        }

        public void Escape() { if (IsOpen && !resolving) Close(false); }

        // ── 가르치는 몸짓 그림 ────────────────────────────
        /// <summary>"self"·"other"·"both" — 몸짓 그림 쪽지. null·""이면 뗌. 닫혀 있으면 다음에 열 때 붙는다.</summary>
        public void SetGestureHint(string kind)
        {
            gestureKind = string.IsNullOrEmpty(kind) ? null : kind.Trim().ToLowerInvariant();
            if (IsOpen) ApplyGesture(true);
        }

        void ApplyGesture(bool sound)
        {
            gestureNote.Clear();
            if (gestureKind == null) { gestureNote.style.display = DisplayStyle.None; return; }
            gestureNote.Add(UIKit.Box("tape tape-top"));
            var row = UIKit.Box("gesture-row"); gestureNote.Add(row);
            bool self = gestureKind == "self" || gestureKind == "both";
            bool other = gestureKind == "other" || gestureKind == "both";
            if (self) row.Add(UIKit.Box("gesture-pic gesture-self"));
            if (self && other) row.Add(UIKit.Box("gesture-sep"));
            if (other) row.Add(UIKit.Box("gesture-pic gesture-other"));
            gestureNote.style.display = DisplayStyle.Flex;
            UIKit.AnimateIn(gestureNote, "note-start", 60);
            if (sound) AudioHub.Play("page", 0.3f, 1.3f);
        }

        // ── 처음 안내(세 걸음) ─────────────────────────────
        void CheckTutorial()
        {
            if (tutStep == 1 && placed.Count > 0) tutStep = 2;
            if (tutStep == 2 && placed.Any(p => p.Word != null)) tutStep = 3;
            tutLayer.style.display = tutStep > 0 && IsOpen ? DisplayStyle.Flex : DisplayStyle.None;
            switch (tutStep)
            {
                case 1: tutNum.text = "①"; tutText.text = "모형을 끌어 오른쪽 판에 놓는다"; break;
                case 2: tutNum.text = "②"; tutText.text = "글자를 조각 위에 놓는다 — 그 글자 색이 입혀진다"; break;
                case 3: tutNum.text = "③"; tutText.text = "다 짰으면 말한다"; break;
            }
            if (tutStep > 0) UIKit.AnimateIn(tutNote, "note-start", 30);
        }

        void FinishTutorial()
        {
            tutStep = 0;
            tutLayer.style.display = DisplayStyle.None;
            Game.I?.State.Set("tut_board");
        }

        void PlaceTutorial()
        {
            if (tutStep == 0 || !IsOpen || tutLayer.panel == null) return;
            VisualElement src = tutStep == 1 ? (palette.childCount > 0 ? palette[0] : null)
                              : tutStep == 2 ? (chips.childCount > 0 ? chips[0] : null)
                              : speakBtn;
            if (src == null || float.IsNaN(src.worldBound.width)) return;
            Vector2 sc = tutLayer.WorldToLocal(src.worldBound.center);
            Vector2 target;
            if (tutStep == 1) target = tutLayer.WorldToLocal(board.worldBound.center);
            else if (tutStep == 2)
            {
                var pv = placed.FirstOrDefault(p => p.Word == null) ?? placed.FirstOrDefault();
                target = pv != null ? tutLayer.WorldToLocal(pv.LocalToWorld(new Vector2(cell / 2f, cell / 2f))) : tutLayer.WorldToLocal(board.worldBound.center);
            }
            else target = sc;

            float nw = tutNote.resolvedStyle.width, nh = tutNote.resolvedStyle.height;
            if (float.IsNaN(nw)) return;
            Vector2 noteTL = tutStep == 3 ? new Vector2(sc.x - nw - 250f, sc.y - nh - 70f) : new Vector2(sc.x + 20f, sc.y - nh - 96f);
            tutNote.style.left = noteTL.x; tutNote.style.top = noteTL.y;

            // 동그라미: 끌어 올 것(①②) 또는 말하기(③)
            var sb = src.worldBound;
            float cw = sb.width + 70f, chh = sb.height + 46f;
            tutCircle.style.width = cw; tutCircle.style.height = chh;
            tutCircle.style.left = sc.x - cw / 2f; tutCircle.style.top = sc.y - chh / 2f;

            // 화살표: 쪽지 → 목표
            Vector2 from = tutStep == 3 ? new Vector2(noteTL.x + nw, noteTL.y + nh * 0.7f) : new Vector2(noteTL.x + nw * 0.8f, noteTL.y + nh);
            Vector2 v = target - from;
            float dist = v.magnitude;
            if (dist < 30f) { tutArrow.style.display = DisplayStyle.None; return; }
            tutArrow.style.display = DisplayStyle.Flex;
            Vector2 tip = target - v.normalized * (tutStep == 3 ? sb.width * 0.45f : 26f);
            float len = Mathf.Max(30f, (tip - from).magnitude);
            float s = Mathf.Clamp(len / 0.968f, 80f, 240f);
            tutArrow.style.width = s; tutArrow.style.height = s;
            tutArrow.style.left = tip.x - 0.828f * s; tutArrow.style.top = tip.y - 0.805f * s;
            float ang = Mathf.Atan2(v.y, v.x) * Mathf.Rad2Deg - Mathf.Atan2(166f, 184f) * Mathf.Rad2Deg;
            UIKit.Rotate(tutArrow, ang);
        }
    }
}
