from pathlib import Path

path = Path("index.html")
content = path.read_text(encoding="utf-8")

marker = "@media(min-width:1550px)"

css = r'''
/* =========================================================
   BREAKERS / HOME NARRATIVE V2
   HOW · ENGINE · QUALITY · SECURITY
   ========================================================= */

/* ---------- HOW ---------- */

.breakers-how{
  padding:52px 0 50px;
  border-top:1px solid var(--line);
  border-bottom:1px solid var(--line);
  background:transparent;
}

.breakers-how h2{
  max-width:820px;
  margin:0;
  font-size:clamp(32px,3.2vw,42px);
  line-height:1.05;
  letter-spacing:-1.8px;
  font-weight:550;
}

.breakers-how h2 strong{
  color:var(--lime);
  font-weight:650;
}

.breakers-how-lead{
  max-width:680px;
  margin:18px 0 30px;
  color:var(--muted);
  font-size:14px;
  line-height:1.65;
}

.breakers-how-grid{
  display:grid;
  grid-template-columns:repeat(3,1fr);
  border-top:1px solid var(--line);
}

.breakers-how-grid>div{
  min-height:100px;
  padding:18px 26px 6px 0;
  border-right:1px solid var(--line);
}

.breakers-how-grid>div+div{
  padding-left:26px;
}

.breakers-how-grid>div:last-child{
  border-right:0;
}

.breakers-how-grid .mono{
  color:var(--lime);
  font-size:9px;
}

.breakers-how-grid p{
  max-width:280px;
  margin:11px 0 0;
  color:#c7d2c1;
  font-size:13px;
  line-height:1.5;
}


/* ---------- AGENTIC ENGINE ---------- */

.breakers-engine{
  padding:54px 0;
  border-bottom:1px solid var(--line);
  background:#0b100e;
}

.breakers-engine-heading{
  display:grid;
  grid-template-columns:1fr 1.45fr;
  column-gap:50px;
  align-items:end;
  margin-bottom:32px;
}

.breakers-engine-heading .small-label{
  grid-column:1 / -1;
  margin-bottom:12px;
}

.breakers-engine-heading h2{
  margin:0;
  font-size:clamp(30px,3vw,40px);
  line-height:1.05;
  letter-spacing:-1.7px;
  font-weight:650;
}

.breakers-engine-heading>p{
  max-width:520px;
  margin:0;
  color:var(--muted);
  font-size:14px;
  line-height:1.65;
}

.breakers-engine-flow{
  display:grid;
  grid-template-columns:1fr 1.18fr 1fr;
  gap:0;
  align-items:stretch;
  border-top:1px solid var(--line);
  border-bottom:1px solid var(--line);
}

.breakers-engine-inputs,
.breakers-engine-outputs{
  display:grid;
  grid-template-rows:repeat(5,1fr);
}

.breakers-engine-inputs{
  border-right:1px solid var(--line);
}

.breakers-engine-outputs{
  border-left:1px solid var(--line);
}

.breakers-engine-inputs>div,
.breakers-engine-outputs>div{
  min-height:62px;
  padding:12px 18px;
  border-bottom:1px solid var(--line);
}

.breakers-engine-inputs>div:last-child,
.breakers-engine-outputs>div:last-child{
  border-bottom:0;
}

.breakers-engine-inputs .mono,
.breakers-engine-outputs .mono{
  color:var(--lime);
  font-size:9px;
}

.breakers-engine-inputs p,
.breakers-engine-outputs p{
  margin:5px 0 0;
  color:var(--muted);
  font-size:11px;
  line-height:1.35;
}

.breakers-engine-core{
  display:flex;
  min-height:310px;
  padding:32px;
  flex-direction:column;
  justify-content:center;
  align-items:center;
  text-align:center;
  position:relative;
}

.breakers-engine-core::before,
.breakers-engine-core::after{
  content:"";
  position:absolute;
  top:50%;
  width:34px;
  height:1px;
  background:var(--lime);
  opacity:.55;
}

.breakers-engine-core::before{
  left:0;
}

.breakers-engine-core::after{
  right:0;
}

.breakers-engine-core .small-label{
  margin-bottom:8px;
  color:var(--lime);
}

.breakers-engine-core h3{
  max-width:260px;
  margin:0;
  font-size:25px;
  line-height:1.05;
  letter-spacing:-1px;
}

.breakers-engine-core .mono{
  max-width:270px;
  margin:18px 0 0;
  color:var(--muted);
  font-size:9px;
  line-height:1.8;
}


/* ---------- QUALITY ENGINEERING ---------- */

.quality-constitution{
  padding:54px 0;
  border-top:0;
  border-bottom:1px solid var(--line);
  background:#0d1210;
  overflow:hidden;
}

.quality-cycle-heading{
  display:grid;
  grid-template-columns:1fr 1.45fr;
  column-gap:50px;
  align-items:end;
  margin-bottom:30px;
}

.quality-cycle-heading .small-label{
  grid-column:1 / -1;
  margin-bottom:12px;
}

.quality-constitution .quality-cycle-heading h2{
  max-width:none;
  margin:0;
  font-size:clamp(30px,3vw,40px);
  line-height:1.05;
  letter-spacing:-1.7px;
  font-weight:650;
}

.quality-cycle-lead{
  max-width:520px;
  margin:0;
  color:var(--muted);
  font-size:14px;
  line-height:1.65;
}

.quality-cycle{
  display:grid;
  grid-template-columns:repeat(5,1fr);
  border-top:1px solid var(--line);
  border-bottom:1px solid var(--line);
}

.quality-cycle-stage{
  min-height:145px;
  padding:20px 20px 18px;
  position:relative;
  border-right:1px solid var(--line);
}

.quality-cycle-stage:last-child{
  border-right:0;
}

.quality-cycle-stage::after{
  content:"→";
  position:absolute;
  top:18px;
  right:-8px;
  z-index:2;
  padding:0 2px;
  background:#0d1210;
  color:var(--lime);
  font-size:13px;
}

.quality-cycle-stage:last-child::after{
  display:none;
}

.quality-cycle-number{
  color:var(--lime);
  font-family:var(--mono);
  font-size:9px;
}

.quality-cycle-stage h3{
  margin:28px 0 8px;
  font-size:15px;
  letter-spacing:-.3px;
}

.quality-cycle-stage p{
  max-width:190px;
  margin:0;
  color:var(--muted);
  font-size:12px;
  line-height:1.5;
}

.quality-cycle-breakers{
  display:flex;
  gap:30px;
  align-items:center;
  padding-top:20px;
}

.quality-cycle-breakers .small-label{
  flex:0 0 auto;
  margin:0;
  color:var(--lime);
}

.quality-cycle-breakers p{
  max-width:760px;
  margin:0;
  color:#c7d2c1;
  font-size:13px;
  line-height:1.55;
}


/* ---------- SECURITY ---------- */

.breakers-security{
  padding:54px 0;
  border-bottom:1px solid var(--line);
  background:#090d0b;
}

.breakers-security-heading{
  display:grid;
  grid-template-columns:1fr 1.45fr;
  column-gap:50px;
  align-items:end;
  margin-bottom:30px;
}

.breakers-security-heading .small-label{
  grid-column:1 / -1;
  margin-bottom:12px;
}

.breakers-security-heading h2{
  margin:0;
  font-size:clamp(30px,3vw,40px);
  line-height:1.05;
  letter-spacing:-1.7px;
  font-weight:650;
}

.breakers-security-heading>p{
  max-width:520px;
  margin:0;
  color:var(--muted);
  font-size:14px;
  line-height:1.65;
}

.breakers-security-grid{
  display:grid;
  grid-template-columns:repeat(4,1fr);
  border-top:1px solid var(--line);
  border-bottom:1px solid var(--line);
}

.breakers-security-item{
  min-height:135px;
  padding:20px;
  border-right:1px solid var(--line);
}

.breakers-security-item:last-child{
  border-right:0;
}

.breakers-security-number{
  color:var(--lime);
  font-family:var(--mono);
  font-size:9px;
}

.breakers-security-item h3{
  margin:28px 0 8px;
  font-size:15px;
  letter-spacing:-.3px;
}

.breakers-security-item p{
  max-width:240px;
  margin:0;
  color:var(--muted);
  font-size:12px;
  line-height:1.5;
}

.breakers-security-note{
  max-width:780px;
  margin:18px 0 0;
  color:var(--muted);
  font-size:11px;
  line-height:1.55;
}


/* ---------- RESPONSIVE ---------- */

@media(max-width:760px){

  .breakers-how,
  .breakers-engine,
  .quality-constitution,
  .breakers-security{
    padding:42px 0;
  }

  .breakers-how h2,
  .breakers-engine-heading h2,
  .quality-constitution .quality-cycle-heading h2,
  .breakers-security-heading h2{
    font-size:32px;
    letter-spacing:-1.3px;
  }

  .breakers-how-grid,
  .breakers-engine-flow,
  .quality-cycle,
  .breakers-security-grid{
    grid-template-columns:1fr;
  }

  .breakers-how-grid>div,
  .breakers-how-grid>div+div{
    min-height:auto;
    padding:17px 0;
    border-right:0;
    border-bottom:1px solid var(--line);
  }

  .breakers-how-grid>div:last-child{
    border-bottom:0;
  }

  .breakers-engine-heading,
  .quality-cycle-heading,
  .breakers-security-heading{
    display:block;
  }

  .breakers-engine-heading h2,
  .quality-cycle-heading h2,
  .breakers-security-heading h2{
    margin-bottom:16px;
  }

  .breakers-engine-inputs,
  .breakers-engine-outputs{
    display:block;
    border:0;
  }

  .breakers-engine-inputs{
    border-bottom:1px solid var(--line);
  }

  .breakers-engine-outputs{
    border-top:1px solid var(--line);
  }

  .breakers-engine-core{
    min-height:210px;
  }

  .breakers-engine-core::before,
  .breakers-engine-core::after{
    display:none;
  }

  .quality-cycle-stage{
    min-height:auto;
    padding:18px 0;
    border-right:0;
    border-bottom:1px solid var(--line);
  }

  .quality-cycle-stage:last-child{
    border-bottom:0;
  }

  .quality-cycle-stage::after{
    display:none;
  }

  .quality-cycle-stage h3,
  .breakers-security-item h3{
    margin:12px 0 6px;
  }

  .quality-cycle-breakers{
    display:block;
  }

  .quality-cycle-breakers p{
    margin-top:10px;
  }

  .breakers-security-item{
    min-height:auto;
    padding:18px 0;
    border-right:0;
    border-bottom:1px solid var(--line);
  }

  .breakers-security-item:last-child{
    border-bottom:0;
  }
}

'''

if content.count(marker) != 1:
    raise RuntimeError(
        f"Esperaba encontrar {marker} una vez; encontré "
        f"{content.count(marker)}. No se modificó index.html."
    )

if "/* BREAKERS / HOME NARRATIVE V2 */" in content:
    raise RuntimeError(
        "El CSS HOME NARRATIVE V2 ya existe. No se modificó index.html."
    )

content = content.replace(marker, css + "\n" + marker, 1)

with path.open("w", encoding="utf-8", newline="") as f:
    f.write(content)

print("OK - CSS HOME NARRATIVE V2 agregado")