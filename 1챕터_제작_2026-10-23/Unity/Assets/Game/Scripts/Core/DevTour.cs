using System;
using System.Collections;
using System.IO;
using System.Linq;
using OUAT.World;
using UnityEngine;

namespace OUAT.Core
{
    /// <summary>
    /// 확인용 자동 둘러보기. 실행판을 `-ouatTour <폴더>`로 켜면 새 게임을 시작해 주요 장면마다 화면을 찍고 끝낸다.
    /// 개발 중 단축키(F5 저장 지우고 처음부터, F6 다음 단계 깃발 건너뛰기)는 `-ouatDev`일 때만.
    /// </summary>
    public class DevTour : MonoBehaviour
    {
        string outDir;
        bool dev;
        int shot;

        [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.AfterSceneLoad)]
        static void Boot()
        {
            var args = Environment.GetCommandLineArgs();
            int i = Array.IndexOf(args, "-ouatTour");
            bool dev = args.Contains("-ouatDev");
            if (i < 0 && !dev && Array.IndexOf(args, "-ouatAutoplay") < 0) return;
            var go = new GameObject("DevTour");
            var t = go.AddComponent<DevTour>();
            t.dev = dev;
            int ap = Array.IndexOf(args, "-ouatAutoplay");
            if (ap >= 0) { t.outDir = ap + 1 < args.Length ? args[ap + 1] : Path.Combine(Application.persistentDataPath, "autoplay"); Directory.CreateDirectory(t.outDir); t.StartCoroutine(t.Autoplay()); return; }
            if (i >= 0) { t.outDir = i + 1 < args.Length ? args[i + 1] : Path.Combine(Application.persistentDataPath, "tour"); Directory.CreateDirectory(t.outDir); t.StartCoroutine(t.Tour()); }
        }

        IEnumerator Snap(string name)
        {
            yield return new WaitForEndOfFrame();
            var path = Path.Combine(outDir, $"{++shot:00}_{name}.png");
            ScreenCapture.CaptureScreenshot(path);
            Debug.Log("[OUAT] tour shot " + path);
            yield return null; yield return null;
        }

        IEnumerator WaitIdle(float max = 30f)
        {
            float t = 0;
            yield return new WaitForSeconds(0.5f);
            while (Game.I != null && Game.I.Busy && t < max) { t += Time.deltaTime; yield return null; }
        }

        IEnumerator Walk(Vector3 p, float max = 25f)
        {
            var g = Game.I;
            // 다른 구역이면 출구를 거쳐 간다(구역 체계, 화-12)
            for (int hop = 0; hop < 6 && AreaSystem.I != null && AreaSystem.I.Of(p) != AreaSystem.I.Active; hop++)
            {
                var ex = AreaSystem.I.ExitToward(p);
                if (ex == null) break;
                var before = AreaSystem.I.Active;
                bool arrived = false;
                g.player.WalkTo(Game.Ground(new Vector3(ex.Pos.x, 0, ex.Pos.y)), () => arrived = true);
                float tt = 0; while (AreaSystem.I.Active == before && tt < max) { tt += Time.deltaTime; yield return null; }
                yield return WaitIdle(10f);
            }
            bool done = false;
            g.player.WalkTo(p, () => done = true);
            float t = 0; while (!done && t < max) { t += Time.deltaTime; yield return null; }
        }

        void WarpTo(Vector3 p)
        {
            var g = Game.I;
            g.player.Warp(p);
            if (AreaSystem.I != null) AreaSystem.I.SetActive(AreaSystem.I.Of(p), snap: true);
        }

        IEnumerator Tour()
        {
            yield return new WaitForSeconds(2f);
            yield return Snap("title");
            var g = Game.I;
            g.NewGame();
            yield return new WaitForSeconds(6f);
            yield return Snap("wake");
            yield return WaitIdle(40f);
            yield return Snap("after_wake");
            // 키노피오에게 다가가기 → 첫 만남
            yield return Walk(g.Npc("kinopio").transform.position);
            yield return new WaitForSeconds(5f);
            yield return Snap("first_meet");
            yield return WaitIdle(60f);
            yield return Snap("kid_at_bolt");
            // 사다리 걸쇠
            var ladder = g.Puzzle("pz_ladder");
            if (ladder) { yield return Walk(ladder.transform.position + Vector3.up * 0); g.Interact(ladder.GetComponentInChildren<Interactable>()); yield return new WaitForSeconds(2.5f); yield return Snap("ladder_hold"); }
            yield return WaitIdle(40f);
            yield return Snap("path_open");
            yield return Walk(g.At("gate"));
            yield return new WaitForSeconds(4f);
            yield return Snap("gate_greet");
            yield return WaitIdle(90f);
            yield return Snap("kid_teaches_done");
            // 대화 1 열기
            var d1 = g.OpenDialogueFor("chief");
            if (d1 != null) { g.StartDialogue(d1); yield return new WaitForSeconds(1.5f); yield return Snap("dialogue1"); g.ui.Escape(); yield return new WaitForSeconds(0.5f); }
            g.ui.ToggleJournal(); yield return new WaitForSeconds(0.8f); yield return Snap("journal"); g.ui.ToggleJournal();
            var ins = g.Data.Inscriptions.Values.FirstOrDefault(x => x.Id == "ins_gate");
            if (ins != null) { g.ui.OpenInscription(ins); yield return new WaitForSeconds(0.8f); yield return Snap("inscription_gate"); g.ui.Escape(); }
            // 광장·밭 둘러보기(카메라 확인)
            foreach (var place in new[] { "plaza", "alley", "field", "pond" })
            {
                WarpTo(g.At(place));
                yield return new WaitForSeconds(3.5f);
                yield return Snap("place_" + place);
            }
            var board = g.Data.Inscriptions.Values.FirstOrDefault(x => x.IsDisplay);
            if (board != null) { g.ui.OpenInscription(board); yield return new WaitForSeconds(0.8f); yield return Snap("picture_board"); g.ui.Escape(); }
            var rd = g.Data.Readables.Values.FirstOrDefault();
            if (rd != null) { g.ui.OpenReadable(rd); yield return new WaitForSeconds(0.8f); yield return Snap("readable"); g.ui.Escape(); }
            yield return new WaitForSeconds(1f);
            Debug.Log("[OUAT] tour done");
            Application.Quit();
        }

        // ── 자동 완주: 목표 대상을 따라 걷고, 퍼즐을 풀고, 대화는 진행 응답으로 통과 ──
        IEnumerator Autoplay()
        {
            yield return new WaitForSeconds(1.5f);
            var g = Game.I;
            g.NewGame();
            StartCoroutine(OpeningSnaps());
            var log = new System.Text.StringBuilder();
            string lastGoal = null; int sameGoal = 0, emptyWaits = 0; float start = Time.time;
            for (int step = 0; step < 220; step++)
            {
                File.WriteAllText(Path.Combine(outDir, "autoplay.txt"), log.ToString());   // 도중에 끊겨도 기록이 남게
                yield return WaitIdle(90f);
                while (g.ui.BlocksWorld && !g.PickMode) { g.ui.Escape(); yield return new WaitForSeconds(0.3f); }
                var goal = g.Data.CurrentGoal(g.State);
                bool noGoal = goal == null || string.IsNullOrEmpty(goal.Text);
                if (noGoal && !g.State.Has("f_end") && emptyWaits < 12) { emptyWaits++; log.AppendLine($"  [NO-GOAL {emptyWaits}] busy={g.Busy}[{g.BusyOwners}] pick={g.PickMode}"); if (g.PickMode) { g.SendMessage("DevPick", "kinopio", SendMessageOptions.DontRequireReceiver); } yield return Snap("nogoal_" + step); yield return new WaitForSeconds(5f); continue; }
                if (g.State.Has("f_end") || noGoal) { log.AppendLine($"[END] step {step} t={Time.time - start:0}s goal={goal?.Text} f_end={g.State.Has("f_end")} flags={string.Join(",", g.State.Flags.Where(f => f.StartsWith("f_")))}"); break; }
                emptyWaits = 0;
                if (goal.Text == lastGoal) sameGoal++; else { sameGoal = 0; lastGoal = goal.Text; log.AppendLine($"[GOAL] t={Time.time - start:0}s {goal.Text} target={J.Str(goal.Raw, "target")} area={AreaSystem.I?.Active} pos={g.player.transform.position} busy={g.Busy}[{g.BusyOwners}]"); yield return Snap("goal_" + step); }
                if (sameGoal > 0) log.AppendLine($"  [SAME {sameGoal}] area={AreaSystem.I?.Active} pos={g.player.transform.position} busy={g.Busy}[{g.BusyOwners}] blocks={g.ui.BlocksWorld}");
                if (sameGoal > 6) { log.AppendLine($"[STUCK] {goal.Text} target={J.Str(goal.Raw, "target")} flags={string.Join(",", g.State.Flags.Where(f => f.StartsWith("f_")))}"); yield return Snap("stuck_" + step); break; }
                var target = J.Str(goal.Raw, "target");
                // 대화가 열린 크리처가 있으면 그쪽 먼저
                var open = g.Data.Dialogues.Values.FirstOrDefault(d => !g.State.Has("done:" + d.Id) && d.OpensWhen.Eval(g.State));
                if (open != null && g.Npc(open.Npc))
                {
                    yield return Walk(g.Npc(open.Npc).transform.position);
                    log.AppendLine($"  [DIALOGUE] {open.Id}");
                    g.StartDialogue(open);
                    yield return new WaitForSeconds(1.2f);
                    yield return Snap("dlg_" + open.Id);
                    g.ui.Escape();
                    yield return new WaitForSeconds(0.4f);
                    var resp = open.Responses.FirstOrDefault(r => r.Progress);
                    if (resp != null)
                    {
                        g.Busy = true;
                        yield return g.RunResponse(open, resp, ChapterData.WordsOf(resp.Spec), false);
                        g.Busy = false;
                        g.State.Set("tut_board"); g.State.Set("done:" + open.Id); g.Fire("done:" + open.Id);
                    }
                    continue;
                }
                if (g.PickMode) { var kid = g.Npc("kinopio"); log.AppendLine("  [PICK]"); yield return Snap("pick"); g.SendMessage("DevPick", "kinopio", SendMessageOptions.DontRequireReceiver); yield return new WaitForSeconds(2f); continue; }
                var pz = g.Puzzle(target);
                if (pz != null && !pz.Solved)
                {
                    var it = pz.GetComponentInChildren<Interactable>();
                    yield return Walk(it ? it.ApproachPoint(g.player.transform.position) : pz.transform.position);
                    log.AppendLine($"  [PUZZLE] {target} available={(it ? it.available : false)}");
                    if (it) g.Interact(it);
                    yield return new WaitForSeconds(2.5f);
                    continue;
                }
                if (target != null && target.StartsWith("look_"))   // 둘러보기: 아직 안 본 물건부터
                {
                    var look = Interactable.All.Where(x => x.id.StartsWith("look_") && !g.State.Has("f_" + x.id)).OrderBy(x => x.id).FirstOrDefault();
                    if (look) { yield return Walk(look.ApproachPoint(g.player.transform.position)); log.AppendLine($"  [LOOK] {look.id}"); g.Interact(look); yield return new WaitForSeconds(3f); continue; }
                }
                var dest = g.At(target);
                var npc = g.Npc(target);
                if (npc && npc.Leading && npc.LeadTarget.HasValue)   // 앞장서는 크리처: 그 목적지(출구면 출구)로 — 사람도 손짓을 보고 그리로 감
                {
                    var lt = npc.LeadTarget.Value;
                    var ex = AreaSystem.I != null ? AreaSystem.I.ExitNear(lt, 3f) : null;
                    log.AppendLine($"  [FOLLOW-LEAD] {target} → {(ex != null ? "exit " + ex.To : lt.ToString())}");
                    yield return Walk(ex != null ? Game.Ground(new Vector3(ex.Pos.x, 0, ex.Pos.y)) : lt);
                    yield return new WaitForSeconds(1.0f);
                    continue;
                }
                if (npc) dest = npc.transform.position + (g.player.transform.position - npc.transform.position).normalized * 1.6f;
                log.AppendLine($"  [WALK] {target} → {dest}");
                yield return Walk(dest);
                if (npc && sameGoal >= 2) { var nit = npc.GetComponent<Interactable>(); if (nit) g.Interact(nit); }
                if (!npc)   // 물건 목표(숨긴 나무 새 찾기 등): 사람처럼 가서 누름
                {
                    var item = Interactable.All.FirstOrDefault(x => x && x.id == target && x.isActiveAndEnabled);
                    if (item) { yield return Walk(item.ApproachPoint(g.player.transform.position)); log.AppendLine($"  [TOUCH] {target}"); g.Interact(item); yield return new WaitForSeconds(2f);
                        if (g.ui.DecreeOpen) { g.ui.DevPeelDecree(); yield return new WaitForSeconds(1.5f); yield return Snap("decree_" + target); log.AppendLine("  [PEEL]"); g.ui.CloseDecree(); yield return new WaitForSeconds(1f); } }
                }
                yield return new WaitForSeconds(1.0f);
            }
            yield return Snap("final");
            File.WriteAllText(Path.Combine(outDir, "autoplay.txt"), log.ToString());
            Debug.Log("[OUAT] autoplay done\n" + log);
            Application.Quit();
        }

        /// <summary>도입(떨어짐) 장면을 시간마다 찍어 흐름을 눈으로 확인.</summary>
        IEnumerator OpeningSnaps()
        {
            float t0 = Time.time;
            foreach (var at in new[] { 2.5f, 4.5f, 6f, 7.5f, 9.5f, 12f, 15f, 18f })
            {
                while (Time.time - t0 < at) yield return null;
                yield return Snap($"open_{at:0.0}s");
            }
        }

        void Update()
        {
            if (!dev || Game.I == null) return;
            if (Input.GetKeyDown(KeyCode.F5)) { GameState.DeleteSave(); UnityEngine.SceneManagement.SceneManager.LoadScene(0); }
        }
    }
}
