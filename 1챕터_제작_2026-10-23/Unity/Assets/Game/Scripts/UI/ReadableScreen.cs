using OUAT.Core;
using UnityEngine;
using UnityEngine.UIElements;

namespace OUAT.UI
{
    /// <summary>사람 글(찢긴 책 낱장 등). 주인공은 사람 글을 바로 읽는다 — 바랜 책 낱장에 붙은 그림과 활자를 그대로 보여 준다.</summary>
    public class ReadableScreen : VisualElement
    {
        readonly VisualElement sheet, picFrame;
        readonly Image picture;
        readonly Label title, body;

        public bool IsOpen => style.display == DisplayStyle.Flex;

        public ReadableScreen()
        {
            AddToClassList("screen"); AddToClassList("readable-screen");
            pickingMode = PickingMode.Position;
            style.display = DisplayStyle.None;
            RegisterCallback<PointerDownEvent>(e => { if (e.target == this) Close(); });
            Add(UIKit.Box("vignette"));
            sheet = UIKit.Box("book-sheet", PickingMode.Position); Add(sheet);
            UIKit.Rotate(sheet, 0.6f);
            picFrame = UIKit.Box("book-pic-frame"); sheet.Add(picFrame);
            UIKit.Rotate(picFrame, -2.2f);
            picture = UIKit.Picture(null, "book-picture"); picFrame.Add(picture);
            picFrame.Add(UIKit.Box("tape tape-corner-a"));
            picFrame.Add(UIKit.Box("tape tape-corner-b"));
            var col = UIKit.Box("book-col"); sheet.Add(col);
            title = UIKit.Text("", "book-title", Face.Serif); col.Add(title);
            col.Add(UIKit.Box("book-rule"));
            body = UIKit.Text("", "book-text", Face.Serif); col.Add(body);
            var foot = UIKit.Box("book-foot"); col.Add(foot);
            foot.Add(UIKit.Text("사람의 글 — 그대로 읽힌다", "book-note", Face.Hand));
            foot.Add(UIKit.InkButton("덮기", Close));
        }

        public void Open(ReadableDef rd)
        {
            title.text = rd.Label;
            body.text = rd.Text;
            var tex = Resources.Load<Texture2D>("Pictures/" + rd.Id);
            picture.image = tex;
            picFrame.style.display = tex ? DisplayStyle.Flex : DisplayStyle.None;
            sheet.EnableInClassList("no-picture", !tex);
            style.display = DisplayStyle.Flex;
            UIKit.AnimateIn(sheet, "page-start", 20);
            AudioHub.Play("page", 0.5f);
        }

        public void Close() { style.display = DisplayStyle.None; }
    }
}
