import React from 'react';
import {AbsoluteFill,Composition,Sequence,OffthreadVideo,registerRoot,staticFile,useCurrentFrame,interpolate,Easing} from 'remotion';
const FPS=30;
const shots=[
 {file:'arrival.mp4',start:0,duration:2,caption:'Check-ins are enabled. The student has not asked a question.',day:'VIRTUAL DAY 3 · No question submitted'},
 {file:'arrival.mp4',start:3,duration:7,caption:'The tutor initiates a review of the two-CPU cache example.',day:'VIRTUAL DAY 4 · Waiting shortened'},
 {file:'reply.mp4',start:0,duration:2.4,caption:'The student opens the check-in to ask a follow-up.',day:'VIRTUAL DAY 4 · Student action'},
 {file:'reply.mp4',start:2.4,duration:3,caption:'“What value does CPU B read next, and why?”',day:'VIRTUAL DAY 4 · Student action'},
 {file:'reply.mp4',start:5.4,duration:9.6,caption:'The cited course explanation identifies x = 1 and the stale-copy update.',day:'VIRTUAL DAY 4 · Source-grounded reply'},
];
const ease=(t:number,a:number,b:number)=>interpolate(t,[a,b],[0,1],{extrapolateLeft:'clamp',extrapolateRight:'clamp',easing:Easing.inOut(Easing.cubic)});
function camera(i:number,t:number){
 if(i===0){let q=ease(t,.35,1.1);return [1+.6*q,-960*q,0];}
 if(i===1)return [1.6,-960,0];
 if(i===2){let q=ease(t,1.7,2.4);return [1.6-.6*q,-960*(1-q),0];}
 if(i===3){let q=ease(t,0,.45);return [1+.6*q,-570*q,-550*q];}
 let q=ease(t,0,.65);return [1.6,-570,-550+470*q];
}
function Cursor({i,t}:{i:number,t:number}){
 let x=0,y=0,opacity=0,click=-10;
 if(i===2&&t>.4&&t<2.1){const q=ease(t,.4,1.6);x=1110+195*q;y=580-138*q;opacity=1;click=1.96;}
 if(i===3&&t>2){const q=ease(t,2,2.55);x=1060+237*q;y=786+43*q;opacity=1;click=2.7;}
 if(!opacity)return null;
 const r=Math.max(0,Math.min(1,(t-click)/.3));
 return <div style={{position:'absolute',left:x,top:y,opacity,pointerEvents:'none'}}>{r>0&&r<1&&<div style={{position:'absolute',width:16+38*r,height:16+38*r,left:-(8+19*r),top:-(8+19*r),border:'2px solid #6756df',borderRadius:'50%',opacity:1-r}}/>}<svg width="23" height="30" viewBox="0 0 23 30" style={{filter:'drop-shadow(0 1px 2px #0006)'}}><path d="M2 1 L2 23 L8 18 L13 28 L17 26 L12 16 L21 15 Z" fill="#191b28" stroke="white" strokeWidth="1.8"/></svg></div>;
}
function Shot({i}:{i:number}){
 const t=useCurrentFrame()/FPS,s=shots[i], [z,x,y]=camera(i,t);
 return <AbsoluteFill><div style={{position:'absolute',left:112,top:62,width:1696,height:954,overflow:'hidden',borderRadius:10,boxShadow:'0 8px 30px #11203916'}}><div style={{position:'absolute',width:1600,height:900,transformOrigin:'0 0',transform:'scale(1.06)'}}><div style={{position:'absolute',width:1600,height:900,transformOrigin:'0 0',transform:`translate(${x}px,${y}px) scale(${z})`}}><OffthreadVideo src={staticFile(s.file)} startFrom={Math.round(s.start*FPS)} playbackRate={i===4?.98:1} muted style={{width:1600,height:900}}/><Cursor i={i} t={t}/></div></div></div><div style={{position:'absolute',top:23,left:112,fontSize:22,fontWeight:650,color:'#202937'}}>SYSTEMS · TWO-CPU CACHE REVIEW</div><div style={{position:'absolute',right:112,top:23,fontSize:21,color:'#4f5664'}}>{s.day}</div><div style={{position:'absolute',bottom:0,left:0,right:0,height:100,background:'#182131',display:'flex',alignItems:'center',justifyContent:'center',padding:'0 100px',fontSize:30,color:'white',textAlign:'center'}}>{s.caption}</div><div style={{position:'absolute',bottom:108,right:122,background:'#fffffff0',padding:'5px 10px',fontSize:17,color:'#555e6e',borderRadius:4}}>Synthetic accounts · Deterministic demo</div></AbsoluteFill>;
}
const Demo=()=>{let offset=0;return <AbsoluteFill style={{background:'#eef0f4',fontFamily:'Arial, sans-serif'}}>{shots.map((s,i)=>{let from=offset;offset+=s.duration*FPS;return <Sequence key={i} from={from} durationInFrames={s.duration*FPS}><Shot i={i}/></Sequence>})}</AbsoluteFill>};
registerRoot(()=> <Composition id="ProductPilot" component={Demo} durationInFrames={720} fps={30} width={1920} height={1080}/>);
