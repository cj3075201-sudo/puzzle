// Windows 실행판 만들기. 배치 실행: tools/unity.ps1 -Method OUAT.EditorTools.BuildPlayer.Windows
using System.IO;
using UnityEditor;
using UnityEditor.Build.Reporting;
using UnityEngine;

namespace OUAT.EditorTools
{
    public static class BuildPlayer
    {
        [MenuItem("OUAT/Build Windows Player")]
        public static void Windows()
        {
            var outDir = Path.GetFullPath(Path.Combine(Application.dataPath, "..", "..", "Builds", "Windows"));
            Directory.CreateDirectory(outDir);
            var opts = new BuildPlayerOptions
            {
                scenes = new[] { "Assets/Game/Scenes/Chapter1.unity" },
                locationPathName = Path.Combine(outDir, "OnceUnderATime.exe"),
                target = BuildTarget.StandaloneWindows64,
                options = BuildOptions.None
            };
            var report = BuildPipeline.BuildPlayer(opts);
            Debug.Log($"[OUAT] Build {report.summary.result} size={report.summary.totalSize} errors={report.summary.totalErrors} → {opts.locationPathName}");
            if (report.summary.result != BuildResult.Succeeded) EditorApplication.Exit(1);
        }
    }
}
