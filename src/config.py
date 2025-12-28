from encodings.base64_codec import base64_decode
from pathlib import Path
import config
import fileUtils
import models
import base64
import tools

defaultSettingBase64 = "I+i/meaYr+S7i+e7jemhteeUn+aIkOeahOmAiemhuQpob21lUGFnZTogIAogIGVuYWJsZTogdHJ1ZQogICPlj6/pgInnmoTlj4LmlbDmnIkge2Jvb2tJRH0ge2Jvb2tDb3Zlcn0ge2Jvb2tOYW1lfSB7Ym9va0F1dGhvcn0ge2Jvb2tEZXNjcmlwdGlvbn0ge0VudGVyfQogIHN0eWxlOiAie2Jvb2tDb3Zlcn17RW50ZXJ95Lmm5ZCNOntib29rTmFtZX17RW50ZXJ95L2c6ICFOntib29rQXV0aG9yfXtFbnRlcn3mj4/ov7A6e2Jvb2tEZXNjcmlwdGlvbn0iCgoj6L+Z5piv5om56YeP5qih5byP55qE5byA5ZCv6YCJ6aG5CmJhdGNoOiAKICBlbmFibGU6IGZhbHNlCiAgI+aJk+W8gOi/meS4qumAiemhueiDveiuqeeoi+W6j+iHquWKqOWkhOeQhuebruW9leS4i+eahOS7peaVsOWtl+S4uuWQjeeahOaWh+S7tuWkue+8jOiAjHF1ZXVl5Lit55qE5YaF5a655Lya6KKr5b+955WlCiAgYXV0bzogdHJ1ZQogICPovpPlhaXkvaDmg7PlpITnkIbnmoTkuabnsY3nmoR1cmzmiJbogIVpZAogIHF1ZXVlOgogICAgLSAxMDAwMDAwMDAKICAgIC0gMjAwMDAwMDAwCgoj6L+Z5piv57yT5a2Y55qE6YCJ6aG5CmNhY2hlOgogICPnlJ/miJDmlofmnKznmoTnvJPlrZgKICB0ZXh0OiB0cnVlCiAgI+WPr+mAieeahOWPguaVsOaciSB7Ym9va0lEfSB7Ym9va0NvdmVyfSB7Ym9va05hbWV9IHtib29rQXV0aG9yfSB7Ym9va0Rlc2NyaXB0aW9ufQogIHRleHRGb2xkZXI6ICJkZWNyeXB0ZWRcXHtib29rSUR9XFx0ZXh0IgogICPnlJ/miJDlm77niYfnmoTnvJPlrZgKICBpbWFnZTogdHJ1ZQogICPlj6/pgInnmoTlj4LmlbDmnIkge2Jvb2tJRH0ge2Jvb2tDb3Zlcn0ge2Jvb2tOYW1lfSB7Ym9va0F1dGhvcn0ge2Jvb2tEZXNjcmlwdGlvbn0KICBpbWFnZUZvbGRlcjogImRlY3J5cHRlZFxce2Jvb2tJRH1cXGltYWdlcyIKCiPml6Xlv5fnm7jlhbPnmoTorr7nva4KbG9nOgogICPlhbPpl63ov5nkuKrpgInpobnkvJrlv73nlaUieHh456ug5pyq6LSt5LmwIueahOitpuWRigogIG5vdEZvdW5kV2FybjogdHJ1ZQoKI+Wkmue6v+eoi+ebuOWFs+eahOiuvue9rgptdWx0aVRocmVhZDoKICAj5pyA5aSn57q/56iL5pWwCiAgbWF4V29ya2VyczogOAoKI+aJi+WKqOebruW9leeahOiuvue9rumAiemhuQptYW51YWxCb29rOgogIGVuYWJsZTogZmFsc2UKICAj5b2T6L+Z5Liq6YCJ6aG55omT5byA5pe277yM56iL5bqP5Lya57uT5ZCIanNvbuaWh+S7tuWSjOS5puexjeWKoOWvhuaWh+S7tuWkue+8jOiLpeafkOS4gOeroOiKguWcqGpzb27kuK3kuI3lrZjlnKjogIzlnKjkuabnsY3liqDlr4bmlofku7blpLnkuK3lrZjlnKjml7bvvIznqIvluo/kuZ/kvJrlsIblhbbovpPlh7rvvIzkvYbmmK8ieHh456ug5pyq6LSt5LmwIueahOaPkOekuuWwhuS8muWkseaViAogIGF1dG9FeHRlbmQ6IHRydWUKICBqc29uU3RyaW5nOiAneyJib29rSUQiOiIxMDAwMDAwMDUiLCJib29rTmFtZSI6IuaIkeeahOWli+aWlyIsImF1dGhvck5hbWUiOiLluIzlsJQiLCJib29rRGVzY3JpcHRpb24iOiLov5nmmK/miJHnmoTlpYvmlpfnmoTnroDku4siLCJjb3ZlclBhdGgiOiIuL2NvdmVyLmpwZyIsImNvbnRlbnRzIjp7IjEwMDAwMDEiOiLnrKzkuIDnq6AiLCIxMDAwMDAyIjoi56ys5LqM56ugIiwiMTAwMDAwMyI6Iue7iOeroCJ9fScKIyB7CiMgICAgICJib29rSUQiOiAiMTAwMDAwMDA1IiwKIyAgICAgImJvb2tOYW1lIjogIuaIkeeahOWli+aWlyIsCiMgICAgICJhdXRob3JOYW1lIjogIuW4jOWwlCIsCiMgICAgICJib29rRGVzY3JpcHRpb24iOiAi6L+Z5piv5oiR55qE5aWL5paX55qE566A5LuLIiwKIyAgICAgImNvdmVyUGF0aCI6ICIuL2NvdmVyLmpwZyIsCiMgICAgICJjb250ZW50cyI6IHsKIyAgICAgICAgICIxMDAwMDAxIjogIuesrOS4gOeroCIsCiMgICAgICAgICAiMTAwMDAwMiI6ICLnrKzkuoznq6AiLAojICAgICAgICAgIjEwMDAwMDMiOiAi57uI56ugIgojICAgICB9CiMgfQ=="

def CalculateParama(book:models.Book):
    book.safeName = tools.SanitizeName(book.name)
    book.decryptedTxt = Path(f"{book.safeName}.txt")
    count = 0
    for chapter in book.chapters:
        count += 1
        chapter.safeTitle = tools.SanitizeName(chapter.title)
        if (config.setting.cache.text == True):
            chapter.decrypted = Path(config.textFolder) / f"{count} {chapter.safeTitle}.txt"
        chapter.key = Path(f"key\\{chapter.id}")
        chapter.encryptedTxt = Path(f"{book.id}\\{chapter.id}.txt")

def init():
    global setting
    if Path(f".\\setting.yaml").exists() == False:
        models.Print.warn(f"[WARN] 找不到 setting.yaml，使用默认配置继续...")
        with open(Path(f".\\setting.yaml"), "w", encoding="utf-8") as f:
            f.write( base64.b64decode(defaultSettingBase64).decode("utf-8"))
    
    try:
        setting = fileUtils.loadSetting(Path(f".\\setting.yaml"))
    except Exception as e:
        models.Print.err(f"[ERR] {e}")
    if setting.batch.enable == True and setting .batch.queue.count == 0:
        models.Print.err("[ERR] 设置文件中的batch目录下的queue项设置错误，因此这个选项将不会起作用")
        setting.batch.enable = False
    global textFolder
    global imageFolder
    textFolder = ""
    imageFolder = ""
    