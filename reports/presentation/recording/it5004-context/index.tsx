import React from 'react';
import {AbsoluteFill,Composition,Sequence,OffthreadVideo,registerRoot,staticFile,useCurrentFrame,interpolate,Easing} from 'remotion';
import clips from './shots.json';
const FPS=30;
const names={CourseSetup:'01  |  IT5004: course setup → student answer',ContinuingSupport:'02  |  IT5004: continuing student support',InstructorReview:'03  |  IT5004: student difficulty → professor review'};
function Cursor({click,t}:{click:any,t:number}){if(!click)return null;const [x,y,at]=click;if(t<at-1||t>at+.6)return null;const q=interpolate(t,[at-1,at],[0,1],{extrapolateLeft:'clamp',extrapolateRight:'clamp'});const r=(t-at)/.4;return <div style={{position:'absolute',left:x-70*(1-q),top:y+45*(1-q),pointerEvents:'none'}}>{r>0&&r<1&&<div style={{position:'absolute',left:-20*r,top:-20*r,width:40*r,height:40*r,border:'3px solid #6e60ea',borderRadius:'50%',opacity:1-r}}/>}<svg width="22" height="29" viewBox="0 0 23 30"><path d="M2 1 L2 23 L8 18 L13 28 L17 26 L12 16 L21 15 Z" fill="#171923" stroke="white" strokeWidth="1.5"/></svg></div>}
function Shot({shot,suite}:{shot:any,suite:string}){
 const t=useCurrentFrame()/FPS;
 const val=(i:number)=>interpolate(t,shot.cam.map((k:any)=>k[0]),shot.cam.map((k:any)=>k[i]),{extrapolateLeft:'clamp',extrapolateRight:'clamp',easing:Easing.inOut(Easing.cubic)});
 const z=val(1),x=Math.max(1600*(1-z),Math.min(0,800-val(2)*z)),y=Math.max(900*(1-z),Math.min(0,450-val(3)*z));
 return <AbsoluteFill style={{background:'#edf0f4',fontFamily:'Arial,sans-serif'}}>
 <div style={{position:'absolute',left:160,top:18,fontSize:23,fontWeight:700,color:'#182f49'}}>{names[suite as keyof typeof names]}</div>
 <div style={{position:'absolute',right:160,top:20,fontSize:18,color:'#526478'}}>{suite==='ContinuingSupport'?'Saved event replay · virtual time':'Synthetic students · saved real-AI responses'}</div>
 <div style={{position:'absolute',left:160,top:60,width:1600,height:900,overflow:'hidden',borderRadius:8,boxShadow:'0 4px 24px #182f4922',background:'white'}}>
 <div style={{position:'absolute',width:1600,height:900,transformOrigin:'0 0',transform:`translate(${x}px,${y}px) scale(${z})`}}>
 <OffthreadVideo src={staticFile(shot.file)} startFrom={Math.round(shot.start*FPS)} playbackRate={shot.rate} muted style={{width:1600,height:900}}/><Cursor click={shot.click} t={t}/></div></div>
 <div style={{position:'absolute',left:0,right:0,bottom:0,height:108,background:'#182f49',color:'white',display:'flex',alignItems:'center',justifyContent:'center',textAlign:'center',padding:'12px 145px',fontSize:32,lineHeight:1.25,fontWeight:500}}>{shot.caption}</div></AbsoluteFill>
}
function Demo({suite}:{suite:keyof typeof clips}){let f=0;return <AbsoluteFill>{clips[suite].map((s,i)=>{const from=f;f+=s.duration*FPS;return <Sequence key={i} from={from} durationInFrames={s.duration*FPS}><Shot shot={s} suite={suite}/></Sequence>})}</AbsoluteFill>}
registerRoot(()=> <>{Object.entries(clips).map(([suite,ss])=><Composition key={suite} id={suite} component={Demo} defaultProps={{suite}} durationInFrames={ss.reduce((n,s)=>n+s.duration,0)*FPS} fps={FPS} width={1920} height={1080}/>)}</>);
