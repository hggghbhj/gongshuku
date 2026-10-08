import json,glob,subprocess,os
v=json.load(open("verified_pdfs.json"))
sus=[r for r in v if r.get("flag","").startswith(("疑似白页","打不开"))]
def render_white(f,page=1):
    try:
        subprocess.run(["pdftoppm","-f",str(page),"-l",str(page),"-r","30","-png",f,"/tmp/pg"],capture_output=True,timeout=40)
        pngs=sorted(glob.glob("/tmp/pg*.png"))
        if not pngs:return "渲染失败"
        # 用 pypdf 不行，用 python 读图的简单方式：检查 PNG 是否非空白（用 file/od 不现实）
        # 用 pdftoppm 已生成，用 ImageMagick 或 python zlib 估算。改用 PIL
        try:
            from PIL import Image
            import numpy as np
            im=Image.open(pngs[0]).convert("L");a=np.array(im)
            nonwhite=(a<235).mean()
            return f"非白像素占比{nonwhite:.3f}"
        except Exception as e:
            # 无 PIL：看 PNG 大小（全白压缩后很小）
            return "png大小%dB"%os.path.getsize(pngs[0])
    except Exception as e:return "err"+str(e)[:30]
for r in sus:
    f=r["file"]
    if not os.path.exists(f):print(r["i"],r["model"],"无文件");continue
    print(r["i"],r["model"][:24],r["flag"],"->",render_white(f))
