#!/usr/bin/env /usr/bin/python3
"""Geometry primitives + matrix helpers for the FNAC 3D scene.

Extracted so both the scene builder and the renderer share one implementation.
Everything is procedural: no external assets, works fully offline.

Coordinate frame: +X = patient's left, +Y = cranial (up), +Z = anterior.
"""
import os

GEO_JS = r"""
/* ------------------------------------------------------------- 4x4 matrices */
function m4(){ return new Float32Array([1,0,0,0, 0,1,0,0, 0,0,1,0, 0,0,0,1]); }
function mul(a,b){
  const o=new Float32Array(16);
  for(let i=0;i<4;i++)for(let j=0;j<4;j++){let s=0;
    for(let k=0;k<4;k++) s+=a[k*4+j]*b[i*4+k]; o[i*4+j]=s;}
  return o;
}
function T(x,y,z){const m=m4();m[12]=x;m[13]=y;m[14]=z;return m;}
function S(x,y,z){const m=m4();m[0]=x;m[5]=y;m[10]=z;return m;}
function RX(a){const m=m4();m[5]=Math.cos(a);m[6]=Math.sin(a);
  m[9]=-Math.sin(a);m[10]=Math.cos(a);return m;}
function RY(a){const m=m4();m[0]=Math.cos(a);m[2]=-Math.sin(a);
  m[8]=Math.sin(a);m[10]=Math.cos(a);return m;}
function RZ(a){const m=m4();m[0]=Math.cos(a);m[1]=Math.sin(a);
  m[4]=-Math.sin(a);m[5]=Math.cos(a);return m;}
function TRS(t,r,s){ let m=T(t[0],t[1],t[2]);
  if(r) m=mul(m,RZ(r[2]||0))&&mul(m,RZ(r[2]||0));
  return m; }

/* --------------------------------------------------------------- primitives */
/* Each returns {pos:[], norm:[], col:[], idx:[]} in a flat, upload-ready form. */

function _fin(p,n,c,idx){ return {pos:p, norm:n, col:c, idx:idx}; }

function ellipsoid(rx,ry,rz,color,seg,ring){
  seg=seg||36; ring=ring||22;
  const p=[],n=[],c=[],idx=[];
  for(let i=0;i<=ring;i++){
    const v=i/ring*Math.PI;
    for(let j=0;j<=seg;j++){
      const u=j/seg*Math.PI*2;
      const x=Math.sin(v)*Math.cos(u), y=Math.cos(v), z=Math.sin(v)*Math.sin(u);
      p.push(x*rx, y*ry, z*rz);
      let nx=x/(rx||1), ny=y/(ry||1), nz=z/(rz||1);
      const l=Math.hypot(nx,ny,nz)||1; n.push(nx/l,ny/l,nz/l);
      c.push(color[0],color[1],color[2]);
    }
  }
  for(let i=0;i<ring;i++)for(let j=0;j<seg;j++){
    const a=i*(seg+1)+j, b=a+seg+1;
    idx.push(a,b,a+1, b,b+1,a+1);
  }
  return _fin(p,n,c,idx);
}

function cylinder(rBottom,rTop,h,color,seg){
  seg=seg||28;
  const p=[],n=[],c=[],idx=[];
  for(let i=0;i<=seg;i++){
    const a=i/seg*Math.PI*2, x=Math.cos(a), z=Math.sin(a);
    p.push(x*rBottom,-h/2,z*rBottom); n.push(x,0,z); c.push(...color);
    p.push(x*rTop,   h/2,z*rTop);    n.push(x,0,z); c.push(...color);
  }
  for(let i=0;i<seg;i++){ const a=i*2; idx.push(a,a+2,a+1, a+1,a+2,a+3); }
  for(const sgn of [-1,1]){
    const base=p.length/3;
    p.push(0,sgn*h/2,0); n.push(0,sgn,0); c.push(...color);
    const r = sgn>0 ? rTop : rBottom;
    for(let i=0;i<=seg;i++){
      const a=i/seg*Math.PI*2;
      p.push(Math.cos(a)*r, sgn*h/2, Math.sin(a)*r);
      n.push(0,sgn,0); c.push(...color);
    }
    for(let i=0;i<seg;i++)
      idx.push(base, base+1+i, base+2+i);
  }
  return _fin(p,n,c,idx);
}

/* capsule: cylinder with hemispherical caps — reads as muscle, handle, cable */
function capsule(r,h,color,seg,ring){
  seg=seg||24; ring=ring||10;
  const p=[],n=[],c=[],idx=[];
  const half=Math.max(0.001, h/2 - r);
  for(let i=0;i<=ring;i++){
    const v=i/ring*Math.PI;
    const y=-half - r*Math.cos(v), rad=r*Math.sin(v);
    for(let j=0;j<=seg;j++){
      const u=j/seg*Math.PI*2;
      const x=Math.cos(u), z=Math.sin(u);
      p.push(x*rad, y, z*rad);
      n.push(x*Math.sin(v), -Math.cos(v), z*Math.sin(v));
      c.push(...color);
    }
  }
  for(let i=0;i<ring;i++)for(let j=0;j<seg;j++){
    const a=i*(seg+1)+j, b=a+seg+1;
    idx.push(a,b,a+1, b,b+1,a+1);
  }
  return _fin(p,n,c,idx);
}

/* torus — used for tracheal cartilage rings */
function torus(R,r,color,seg,ring){
  seg=seg||30; ring=ring||10;
  const p=[],n=[],c=[],idx=[];
  for(let i=0;i<=seg;i++){
    const u=i/seg*Math.PI*2, cu=Math.cos(u), su=Math.sin(u);
    for(let j=0;j<=ring;j++){
      const v=j/ring*Math.PI*2, cv=Math.cos(v), sv=Math.sin(v);
      p.push((R+r*cv)*cu, r*sv, (R+r*cv)*su);
      n.push(cv*cu, sv, cv*su);
      c.push(...color);
    }
  }
  for(let i=0;i<seg;i++)for(let j=0;j<ring;j++){
    const a=i*(ring+1)+j, b=a+ring+1;
    idx.push(a,b,a+1, b,b+1,a+1);
  }
  return _fin(p,n,c,idx);
}

function box(w,h,d,color){
  const p=[],n=[],c=[],idx=[];
  const F=[[[1,1,-1],[-1,1,-1],[-1,-1,-1],[1,-1,-1],[0,0,-1]],
           [[1,1,1],[1,-1,1],[-1,-1,1],[-1,1,1],[0,0,1]],
           [[1,1,-1],[1,1,1],[-1,1,1],[-1,1,-1],[0,1,0]],
           [[1,-1,-1],[-1,-1,-1],[-1,-1,1],[1,-1,1],[0,-1,0]],
           [[1,1,-1],[1,-1,-1],[1,-1,1],[1,1,1],[1,0,0]],
           [[-1,1,-1],[-1,1,1],[-1,-1,1],[-1,-1,-1],[-1,0,0]]];
  for(const f of F){
    const base=p.length/3;
    for(let i=0;i<4;i++){
      const v=f[i];
      p.push(v[0]*w/2, v[1]*h/2, v[2]*d/2);
      n.push(f[4][0], f[4][1], f[4][2]);
      c.push(...color);
    }
    idx.push(base,base+1,base+2, base,base+2,base+3);
  }
  return _fin(p,n,c,idx);
}

function disc(r,color,seg){
  seg=seg||26;
  const p=[0,0,0, 0,1,0,  ...color], n=[0,1,0,0,1,0,0,1,0],
        c=[...color,...color,...color], idx=[];
  for(let i=0;i<=seg;i++){
    const a=i/seg*Math.PI*2;
    p.push(Math.cos(a)*r, 0, Math.sin(a)*r);
    n.push(0,1,0); c.push(...color);
  }
  for(let i=0;i<seg;i++) idx.push(0, 2+i, 2+i+1);
  return _fin(p,n,c,idx);
}

/* cone — the ultrasound beam volume */
function cone(r,h,color,seg){
  seg=seg||28;
  const p=[],n=[],c=[],idx=[];
  const apex=[0,-h/2,0];
  const slope=Math.atan2(r,h);
  for(let i=0;i<=seg;i++){
    const a=i/seg*Math.PI*2;
    const x=Math.cos(a), z=Math.sin(a);
    p.push(apex[0],apex[1],apex[2]);
    n.push(x*Math.sin(slope), -Math.cos(slope), z*Math.sin(slope));
    c.push(...color);
    p.push(x*r, h/2, z*r);
    n.push(x*Math.sin(slope), -Math.cos(slope), z*Math.sin(slope));
    c.push(...color);
  }
  for(let i=0;i<seg;i++){ const a=i*2; idx.push(a,a+1,a+2); }
  const base=p.length/3;
  p.push(0,h/2,0); n.push(0,1,0); c.push(...color);
  for(let i=0;i<=seg;i++){
    const a=i/seg*Math.PI*2;
    p.push(Math.cos(a)*r, h/2, Math.sin(a)*r); n.push(0,1,0); c.push(...color);
  }
  for(let i=0;i<seg;i++) idx.push(base, base+1+i, base+2+i);
  return _fin(p,n,c,idx);
}

/* A proper needle: shaft, tapered bevel tip, and a colour-coded hub. Built
   along +Y so the caller can aim it by rotation. */
function needle(rShaft, rTip, len, color, seg){
  const parts=[];
  const body = cylinder(rShaft, rShaft, len*0.86, color, seg||18);
  const tip  = cone(rShaft, len*0.14, [0.97,0.98,1.0], seg||18);
  // shift the tip to the top of the shaft
  const tipT = new Float32Array(tip.pos.length);
  for(let i=0;i<tip.pos.length;i+=3){
    tipT[i]=tip.pos[i]; tipT[i+1]=tip.pos[i+1]+len*0.43; tipT[i+2]=tip.pos[i+2];
  }
  return concat([body, {pos:tipT, norm:tip.norm, col:tip.col, idx:tip.idx}]);
}

/* merge geometry lists, offsetting indices */
function concat(list){
  const p=[],n=[],c=[],idx=[]; let base=0;
  for(const g of list){
    for(let i=0;i<g.pos.length;i++) p.push(g.pos[i]);
    for(let i=0;i<g.norm.length;i++) n.push(g.norm[i]);
    for(let i=0;i<g.col.length;i++) c.push(g.col[i]);
    for(let i=0;i<g.idx.length;i++) idx.push(g.idx[i]+base);
    base += g.pos.length/3;
  }
  return _fin(p,n,c,idx);
}

const GEO = {m4,mul,T,S,RX,RY,RZ,TRS,ellipsoid,cylinder,capsule,torus,box,
             disc,cone,needle,concat};
"""


def main():
    out = "/home/alex/Documents/FNAC_Webapp/geometry.js"
    with open(out, "w") as fh:
        fh.write(GEO_JS)
    print("wrote", out, len(GEO_JS), "bytes")


if __name__ == "__main__":
    main()
