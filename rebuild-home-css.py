from pathlib import Path

path = Path("index.html")
content = path.read_text(encoding="utf-8")

marker = "@media(min-width:1550px)"

css = r'''
/* =========================================================
   BREAKERS / HERO V2
   ========================================================= */

.hero-v2{
  position:relative;
  padding:62px 0 0;
  overflow:hidden;
  border-bottom:1px solid var(--line);
  background:
    radial-gradient(circle at 77% 30%,rgba(0,174,239,.08),transparent 24%),
    linear-gradient(180deg,#090d0b 0%,#080c0a 100%);
}

.hero-v2::before{
  content:"";
  position:absolute;
  inset:0;
  pointer-events:none;
  opacity:.12;
  background-image:
    linear-gradient(rgba(208,247,122,.06) 1px,transparent 1px),
    linear-gradient(90deg,rgba(208,247,122,.04) 1px,transparent 1px);
  background-size:72px 72px;
}

.hero-v2 .wrap{
  position:relative;
  z-index:1;
}

.hero-v2-main{
  display:grid;
  grid-template-columns:minmax(0,.92fr) minmax(440px,1.08fr);
  gap:70px;
  align-items:center;
  min-height:500px;
  padding-bottom:55px;
}

.hero-v2-copy{
  max-width:600px;
}

.hero-v2-copy .small-label{
  display:block;
  margin-bottom:20px;
  color:var(--lime);
  font-size:9px;
  letter-spacing:1.7px;
}

.hero-v2-copy h1{
  margin:0;
  font-size:clamp(52px,5.6vw,76px);
  line-height:.91;
  letter-spacing:-4px;
  font-weight:650;
}

.hero-v2-copy h1 strong{
  color:var(--lime);
  font-weight:650;
}

.hero-v2-lead{
  max-width:480px;
  margin:26px 0 0;
  color:#9ba89f;
  font-size:14px;
  line-height:1.65;
}

.hero-v2-cta{
  display:inline-flex;
  align-items:center;
  gap:34px;
  margin-top:30px;
  padding:12px 17px;
  border:1px solid rgba(208,247,122,.55);
  color:var(--lime);
  font-family:var(--mono);
  font-size:10px;
  letter-spacing:.5px;
  text-decoration:none;
  text-transform:uppercase;
  transition:.2s ease;
}

.hero-v2-cta:hover{
  background:var(--lime);
  color:#071008;
}

.hero-v2-demo{
  display:flex;
  justify-content:flex-end;
  align-items:center;
}

.hero-v2-demo-frame{
  position:relative;
  width:100%;
  max-width:600px;
  aspect-ratio:1.55 / 1;
  display:flex;
  justify-content:center;
  align-items:center;
  overflow:hidden;
  border:1px solid rgba(208,247,122,.22);
  background:
    linear-gradient(135deg,rgba(208,247,122,.055),transparent 40%),
    #0d1310;
  box-shadow:
    0 0 0 1px rgba(0,0,0,.7),
    0 30px 80px rgba(0,0,0,.28);
}

.hero-v2-demo-frame::before{
  content:"";
  position:absolute;
  inset:0;
  opacity:.16;
  background-image:
    linear-gradient(rgba(208,247,122,.16) 1px,transparent 1px),
    linear-gradient(90deg,rgba(208,247,122,.10) 1px,transparent 1px);
  background-size:28px 28px;
  mask-image:linear-gradient(to bottom,black,transparent 88%);
}

.hero-v2-demo-frame::after{
  content:"BREAKERS / SYSTEM PREVIEW";
  position:absolute;
  top:15px;
  left:17px;
  color:#68756d;
  font-family:var(--mono);
  font-size:8px;
  letter-spacing:1px;
}

.hero-v2-demo-button{
  position:relative;
  z-index:2;
  display:flex;
  align-items:center;
  gap:18px;
  padding:12px 16px;
  border:1px solid rgba(208,247,122,.65);
  background:rgba(7,12,9,.88);
  color:var(--lime);
  font-family:var(--mono);
  font-size:10px;
  text-transform:uppercase;
  cursor:pointer;
}

.hero-v2-demo-button span{
  font-size:14px;
}

.hero-v2-principles{
  display:grid;
  grid-template-columns:1fr 1fr 1fr 1.25fr;
  min-height:160px;
  border-top:1px solid var(--line);
}

.hero-principle{
  display:grid;
  grid-template-columns:70px 1fr;
  gap:18px;
  align-items:center;
  min-width:0;
  padding:25px 25px 25px 0;
  border-right:1px solid var(--line);
}

.hero-principle + .hero-principle{
  padding-left:25px;
}

.hero-principle-icon{
  width:62px;
  height:62px;
  display:flex;
  justify-content:center;
  align-items:center;
  position:relative;
  color:var(--lime);
  font-family:var(--mono);
  font-size:32px;
  border:1px solid rgba(208,247,122,.24);
  background:
    radial-gradient(circle,rgba(208,247,122,.08),transparent 65%);
}

.hero-principle-icon::before,
.hero-principle-icon::after{
  content:"";
  position:absolute;
  background:var(--lime);
  opacity:.35;
}

.hero-principle-icon::before{
  width:76px;
  height:1px;
}

.hero-principle-icon::after{
  width:1px;
  height:76px;
}

.hero-principle h2{
  margin:0;
  color:var(--lime);
  font-size:15px;
  line-height:1.05;
  letter-spacing:-.3px;
}

.hero-principle p{
  margin:8px 0 0;
  color:#87948c;
  font-size:10px;
  line-height:1.45;
}

.hero-v2-manifesto{
  display:flex;
  align-items:center;
  padding:25px 0 25px 34px;
  color:var(--lime);
  font-family:var(--mono);
  font-size:11px;
  line-height:1.65;
  letter-spacing:.2px;
}


/* HERO V2 / MOBILE */

@media(max-width:900px){

  .hero-v2{
    padding-top:42px;
  }

  .hero-v2-main{
    grid-template-columns:1fr;
    gap:38px;
    min-height:0;
    padding-bottom:42px;
  }

  .hero-v2-copy h1{
    font-size:clamp(48px,13vw,68px);
    letter-spacing:-3px;
  }

  .hero-v2-demo{
    justify-content:flex-start;
  }

  .hero-v2-demo-frame{
    max-width:none;
  }

  .hero-v2-principles{
    grid-template-columns:1fr;
  }

  .hero-principle,
  .hero-principle + .hero-principle{
    padding:20px 0;
    border-right:0;
    border-bottom:1px solid var(--line);
  }

  .hero-v2-manifesto{
    padding:24px 0;
  }
}

'''

if content.count(marker) != 1:
    raise RuntimeError(
        f"Esperaba encontrar {marker} una vez; encontré "
        f"{content.count(marker)}. No se modificó index.html."
    )

if "BREAKERS / HERO V2" in content:
    raise RuntimeError(
        "El CSS HERO V2 ya existe. No se modificó index.html."
    )

content = content.replace(marker, css + "\n" + marker, 1)

with path.open("w", encoding="utf-8", newline="") as f:
    f.write(content)

print("OK - CSS HERO V2 agregado")