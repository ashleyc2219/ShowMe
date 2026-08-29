/*
 * GENERATED FILE — 由 overlay/build.sh 產生，不要手動編輯。
 * 要改邏輯請改 overlay/overlay.src.js 後重跑 ./build.sh。
 */

/* ===== vendor: Driver.js（MIT）— 版本與授權見 vendor/LICENSE ===== */
this.driver=this.driver||{},this.driver.js=(function(e){Object.defineProperty(e,Symbol.toStringTag,{value:`Module`});let t=[`pointerdown`,`mousedown`,`pointerup`,`mouseup`,`click`],n=new WeakMap;function r(e,r,a){i(e);let o=t=>{let n=t.target;e.contains(n)&&((!a||a(n))&&(t.preventDefault(),t.stopPropagation(),t.stopImmediatePropagation()),t.type===`click`&&r?.(t))};for(let e of t)document.addEventListener(e,o,!0);n.set(e,o)}function i(e){let r=n.get(e);if(r){for(let e of t)document.removeEventListener(e,r,!0);n.delete(e)}}function a(e,t){let n=e.wrapper.getBoundingClientRect();return{width:n.width+t,height:n.height+t,realWidth:n.width,realHeight:n.height}}function o(e,t){let{elementDimensions:n,popoverDimensions:r,popoverPadding:i,popoverArrowDimensions:a}=t;return e===`start`?Math.max(Math.min(n.top-i,window.innerHeight-r.realHeight-a.width),a.width):e===`end`?Math.max(Math.min(n.top-r?.realHeight+n.height+i,window.innerHeight-r?.realHeight-a.width),a.width):e===`center`?Math.max(Math.min(n.top+n.height/2-r?.realHeight/2,window.innerHeight-r?.realHeight-a.width),a.width):0}function s(e,t){let{elementDimensions:n,popoverDimensions:r,popoverPadding:i,popoverArrowDimensions:a}=t;return e===`start`?Math.max(Math.min(n.left-i,window.innerWidth-r.realWidth-a.width),a.width):e===`end`?Math.max(Math.min(n.left-r?.realWidth+n.width+i,window.innerWidth-r?.realWidth-a.width),a.width):e===`center`?Math.max(Math.min(n.left+n.width/2-r?.realWidth/2,window.innerWidth-r?.realWidth-a.width),a.width):0}function c(e,t,n){let{align:r,side:i}=n,c=n.centered?`over`:i,l=n.padding,u=a(e,n.offset),d=e.arrow.getBoundingClientRect(),p=t.getBoundingClientRect(),m=p.top-u.height,h=m>=0,g=window.innerHeight-(p.bottom+u.height),_=g>=0,v=p.left-u.width,y=v>=0,b=window.innerWidth-(p.right+u.width),x=b>=0,S=!h&&!_&&!y&&!x,C=c;if(c===`top`&&h?x=y=_=!1:c===`bottom`&&_?x=y=h=!1:c===`left`&&y?x=h=_=!1:c===`right`&&x&&(y=h=_=!1),c===`over`){let t=window.innerWidth/2-u.realWidth/2,n=window.innerHeight/2-u.realHeight/2;e.wrapper.style.left=`${t}px`,e.wrapper.style.right=`auto`,e.wrapper.style.top=`${n}px`,e.wrapper.style.bottom=`auto`}else if(S){let t=window.innerWidth/2-u?.realWidth/2;e.wrapper.style.left=`${t}px`,e.wrapper.style.right=`auto`,e.wrapper.style.bottom=`10px`,e.wrapper.style.top=`auto`}else if(y){let t=Math.min(v,window.innerWidth-u?.realWidth-d.width),n=o(r,{elementDimensions:p,popoverDimensions:u,popoverPadding:l,popoverArrowDimensions:d});e.wrapper.style.left=`${t}px`,e.wrapper.style.top=`${n}px`,e.wrapper.style.bottom=`auto`,e.wrapper.style.right=`auto`,C=`left`}else if(x){let t=Math.min(b,window.innerWidth-u?.realWidth-d.width),n=o(r,{elementDimensions:p,popoverDimensions:u,popoverPadding:l,popoverArrowDimensions:d});e.wrapper.style.right=`${t}px`,e.wrapper.style.top=`${n}px`,e.wrapper.style.bottom=`auto`,e.wrapper.style.left=`auto`,C=`right`}else if(h){let t=Math.min(m,window.innerHeight-u.realHeight-d.width),n=s(r,{elementDimensions:p,popoverDimensions:u,popoverPadding:l,popoverArrowDimensions:d});e.wrapper.style.top=`${t}px`,e.wrapper.style.left=`${n}px`,e.wrapper.style.bottom=`auto`,e.wrapper.style.right=`auto`,C=`top`}else if(_){let t=Math.min(g,window.innerHeight-u?.realHeight-d.width),n=s(r,{elementDimensions:p,popoverDimensions:u,popoverPadding:l,popoverArrowDimensions:d});e.wrapper.style.left=`${n}px`,e.wrapper.style.bottom=`${t}px`,e.wrapper.style.top=`auto`,e.wrapper.style.right=`auto`,C=`bottom`}f(e,S?`over`:C,r,t),[...e.wrapper.classList].filter(e=>e.startsWith(`driver-popover-side-`)||e.startsWith(`driver-popover-align-`)).forEach(t=>e.wrapper.classList.remove(t)),e.wrapper.classList.add(`driver-popover-side-${C}`),e.wrapper.classList.add(`driver-popover-align-${r}`)}function l(e,t,n,r,i,a=10){let o=r-n;return e<=n&&t>=r?i===`start`?15+a/2:i===`end`?o-15-a/2:o/2:(Math.min(Math.max(e,n),r)+Math.min(Math.max(t,n),r))/2-n}function u(e,t,n=10){let r=t-15-n;if(r<15)return Math.max(0,(t-n)/2);let i=e-n/2;return Math.min(Math.max(i,15),r)}function d(e,t,n){return e===`left`||e===`right`?t.bottom>n.top&&t.top<n.bottom?e:t.bottom<=n.top?`bottom`:`top`:t.right>n.left&&t.left<n.right?e:t.right<=n.left?`right`:`left`}function f(e,t,n,r){let i=e.arrow;if(i.className=`driver-popover-arrow`,i.style.top=``,i.style.right=``,i.style.bottom=``,i.style.left=``,t===`over`){i.classList.add(`driver-popover-arrow-none`);return}let a=r.getBoundingClientRect(),o=e.wrapper.getBoundingClientRect(),s=d(t,a,o);i.classList.add(`driver-popover-arrow-side-${s}`);let c=i.getBoundingClientRect().width||10;if(s===`left`||s===`right`){let e=l(a.top,a.bottom,o.top,o.bottom,n,c);i.style.top=`${u(e,o.height,c)}px`}else{let e=l(a.left,a.right,o.left,o.right,n,c);i.style.left=`${u(e,o.width,c)}px`}}function p(e){return typeof e==`function`?e():typeof e==`string`?document.querySelector(e):e}function m(e){let t=window.getComputedStyle(e);return[t.overflow,t.overflowX,t.overflowY].some(e=>e===`auto`||e===`scroll`)}function h(e,t,n,r){return(e/=r/2)<1?n/2*e*e+t:-n/2*(--e*(e-2)-1)+t}function g(e){let t=`a[href]:not([disabled]), button:not([disabled]), textarea:not([disabled]), input[type="text"]:not([disabled]), input[type="radio"]:not([disabled]), input[type="checkbox"]:not([disabled]), select:not([disabled])`;return e.flatMap(e=>{let n=e.matches(t),r=Array.from(e.querySelectorAll(t));return[...n?[e]:[],...r]}).filter(e=>getComputedStyle(e).pointerEvents!==`none`&&b(e))}function _(e,t){if(!e||y(e))return;let n=e.offsetHeight>window.innerHeight;e.scrollIntoView({behavior:!t||v(e)?`auto`:`smooth`,inline:`center`,block:n?`start`:`center`})}function v(e){if(!e||!e.parentElement)return;let t=e.parentElement;return t.scrollHeight>t.clientHeight}function y(e){let t=e.getBoundingClientRect();return t.top>=0&&t.left>=0&&t.bottom<=(window.innerHeight||document.documentElement.clientHeight)&&t.right<=(window.innerWidth||document.documentElement.clientWidth)}function b(e){return!!(e.offsetWidth||e.offsetHeight||e.getClientRects().length)}function x(e){e&&(e.wrapper.style.display=`none`)}function S(e,t){let n=ee();document.body.appendChild(n.wrapper);let{title:i,description:a,showButtons:o,disableButtons:s,showProgress:l,nextBtnText:u,prevBtnText:d,progressText:f}=t;n.nextButton.innerHTML=u,n.previousButton.innerHTML=d,n.progress.innerHTML=f,t.doneButton&&n.nextButton.classList.add(`driver-popover-done-btn`),i?(n.title.innerHTML=i,n.title.style.display=`block`):n.title.style.display=`none`,a?(n.description.innerHTML=a,n.description.style.display=`block`):n.description.style.display=`none`;let p=o.includes(`next`)||o.includes(`previous`)||l;n.closeButton.style.display=o.includes(`close`)?`block`:`none`,p?(n.footer.style.display=`flex`,n.progress.style.display=l?`block`:`none`,n.nextButton.style.display=o.includes(`next`)?`block`:`none`,n.previousButton.style.display=o.includes(`previous`)?`block`:`none`):n.footer.style.display=`none`,s.includes(`next`)&&(n.nextButton.disabled=!0,n.nextButton.classList.add(`driver-popover-btn-disabled`)),s.includes(`previous`)&&(n.previousButton.disabled=!0,n.previousButton.classList.add(`driver-popover-btn-disabled`)),s.includes(`close`)&&(n.closeButton.disabled=!0,n.closeButton.classList.add(`driver-popover-btn-disabled`));let m=n.wrapper;m.style.display=`block`,m.style.left=``,m.style.top=``,m.style.bottom=``,m.style.right=``,m.id=`driver-popover-content`,m.setAttribute(`role`,`dialog`),m.setAttribute(`aria-labelledby`,`driver-popover-title`),m.setAttribute(`aria-describedby`,`driver-popover-description`);let h=n.arrow;h.className=`driver-popover-arrow`,m.className=`driver-popover ${t.popoverClass||``}`.trim(),r(n.wrapper,e=>{let n=e.target;if(n.closest(`.driver-popover-next-btn`))return t.onNextClick?.();if(n.closest(`.driver-popover-prev-btn`))return t.onPrevClick?.();if(n.closest(`.driver-popover-close-btn`))return t.onCloseClick?.()},e=>n.description.contains(e)||n.title.contains(e)?!1:!!e.closest(`.driver-popover-prev-btn, .driver-popover-next-btn, .driver-popover-close-btn`)),t.onRender?.(n),c(n,e,t.position),C(n,e,t.position),_(m,t.smoothScroll);let v=g([m,e]);return v.length>0&&v[0].focus(),n}function C(e,t,n){e.wrapper.querySelectorAll(`img`).forEach(r=>{if(r.complete)return;let i=()=>c(e,t,n);r.addEventListener(`load`,i,{once:!0}),r.addEventListener(`error`,i,{once:!0})})}function ee(){let e=document.createElement(`div`);e.classList.add(`driver-popover`);let t=document.createElement(`div`);t.classList.add(`driver-popover-arrow`);let n=document.createElement(`header`);n.id=`driver-popover-title`,n.classList.add(`driver-popover-title`),n.style.display=`none`,n.innerText=`Popover Title`;let r=document.createElement(`div`);r.id=`driver-popover-description`,r.classList.add(`driver-popover-description`),r.style.display=`none`,r.innerText=`Popover description is here`;let i=document.createElement(`button`);i.type=`button`,i.classList.add(`driver-popover-close-btn`),i.setAttribute(`aria-label`,`Close`),i.innerHTML=`&times;`;let a=document.createElement(`footer`);a.classList.add(`driver-popover-footer`);let o=document.createElement(`span`);o.classList.add(`driver-popover-progress-text`),o.innerText=``;let s=document.createElement(`span`);s.classList.add(`driver-popover-navigation-btns`);let c=document.createElement(`button`);c.type=`button`,c.classList.add(`driver-popover-prev-btn`,`driver-popover-footer-btn`),c.innerHTML=`Previous`;let l=document.createElement(`button`);return l.type=`button`,l.classList.add(`driver-popover-next-btn`,`driver-popover-footer-btn`),l.innerHTML=`Next`,s.appendChild(c),s.appendChild(l),a.appendChild(o),a.appendChild(s),e.appendChild(i),e.appendChild(t),e.appendChild(n),e.appendChild(r),e.appendChild(a),{wrapper:e,arrow:t,title:n,description:r,footer:a,previousButton:c,nextButton:l,closeButton:i,footerButtons:s,progress:o}}function w(e){e&&(i(e.wrapper),e.wrapper.parentElement?.removeChild(e.wrapper))}function T(e,t){let n=window.innerWidth,r=window.innerHeight,i=t.padding,a=t.radius,o=e.width+i*2,s=e.height+i*2,c=Math.min(a,o/2,s/2),l=Math.floor(Math.max(c,0)),u=e.x-i+l,d=e.y-i,f=o-l*2,p=s-l*2;return`M${n},0L0,0L0,${r}L${n},${r}L${n},0Z
    M${u},${d} h${f} a${l},${l} 0 0 1 ${l},${l} v${p} a${l},${l} 0 0 1 -${l},${l} h-${f} a${l},${l} 0 0 1 -${l},-${l} v-${p} a${l},${l} 0 0 1 ${l},-${l} z`}function E(e,t,n,r,i){let a=e.getState(`__activeStagePosition`),o=a||r.getBoundingClientRect(),s=i.getBoundingClientRect();a={x:h(t,o.x,s.x-o.x,n),y:h(t,o.y,s.y-o.y,n),width:h(t,o.width,s.width-o.width,n),height:h(t,o.height,s.height-o.height,n)},A(e,a),e.setState(`__activeStagePosition`,a)}function D(e,t){if(!t)return;let n=t.getBoundingClientRect(),r={x:n.x,y:n.y,width:n.width,height:n.height};e.setState(`__activeStagePosition`,r),A(e,r)}function O(e){let t=e.getState(`__activeStagePosition`),n=e.getState(`__overlaySvg`);if(!t)return;if(!n){console.warn(`No stage svg found.`);return}let r=window.innerWidth,i=window.innerHeight;n.setAttribute(`viewBox`,`0 0 ${r} ${i}`)}function k(e,t){let n=M(e,t);document.body.appendChild(n),r(n,t=>{t.target.tagName===`path`&&e.emit(`overlayClick`)}),e.setState(`__overlaySvg`,n)}function A(e,t){let n=e.getState(`__overlaySvg`);if(!n){k(e,t);return}let r=n.firstElementChild;if(r?.tagName!==`path`)throw Error(`no path element found in stage svg`);r.setAttribute(`d`,T(t,j(e)))}function j(e){return{padding:e.getConfig(`stagePadding`)||0,radius:e.getConfig(`stageRadius`)||0}}function M(e,t){let n=window.innerWidth,r=window.innerHeight,i=document.createElementNS(`http://www.w3.org/2000/svg`,`svg`);i.classList.add(`driver-overlay`,`driver-overlay-animated`),i.setAttribute(`viewBox`,`0 0 ${n} ${r}`),i.setAttribute(`xmlSpace`,`preserve`),i.setAttribute(`xmlnsXlink`,`http://www.w3.org/1999/xlink`),i.setAttribute(`version`,`1.1`),i.setAttribute(`preserveAspectRatio`,`xMinYMin slice`),i.style.fillRule=`evenodd`,i.style.clipRule=`evenodd`,i.style.strokeLinejoin=`round`,i.style.strokeMiterlimit=`2`,i.style.zIndex=`10000`,i.style.position=`fixed`,i.style.top=`0`,i.style.left=`0`,i.style.width=`100%`,i.style.height=`100%`;let a=document.createElementNS(`http://www.w3.org/2000/svg`,`path`);return a.setAttribute(`d`,T(t,j(e))),a.style.fill=e.getConfig(`overlayColor`)||`rgb(0,0,0)`,a.style.opacity=`${e.getConfig(`overlayOpacity`)}`,a.style.pointerEvents=`auto`,a.style.cursor=`auto`,i.appendChild(a),i}function N(e){let t=e.getState(`__overlaySvg`);t&&(i(t),t.remove())}let P=`{{current}} of {{total}}`;function F(e,t){return!(t.skipMissingElement??e.getConfig(`skipMissingElement`))||!t.element?!1:!p(t.element)}function I(e,t,n){let r=e.getConfig(`steps`)||[];for(let i=t;i>=0&&i<r.length;i+=n)if(!F(e,r[i]))return i}function L(e,t){let n=e.getState(`activeIndex`),r=n!==void 0&&I(e,n+1,1)===void 0,i=t?.popover?.onDoneClick||e.getConfig(`onDoneClick`);return r&&i?i:t?.popover?.onNextClick||e.getConfig(`onNextClick`)}function R(e,t){return t?.popover?.onPrevClick||e.getConfig(`onPrevClick`)}function z(e,t){return t?.popover?.onCloseClick||e.getConfig(`onCloseClick`)}function B(e,t,n){let r=e.getConfig(`steps`)||[],i=r[t],a=i.popover||{},o=I(e,t+1,1)!==void 0,s=I(e,t-1,-1)!==void 0,c=a.doneBtnText||e.getConfig(`doneBtnText`)||`Done`,l=e.getConfig(`allowClose`),u=a.showProgress===void 0?e.getConfig(`showProgress`):a.showProgress,d=(a.progressText||e.getConfig(`progressText`)||P).replace(`{{current}}`,`${t+1}`).replace(`{{total}}`,`${r.length}`),f=a.showButtons||e.getConfig(`showButtons`),p=[`next`,`previous`,...l?[`close`]:[]].filter(e=>!f?.length||f.includes(e)),m=a.onNextClick||e.getConfig(`onNextClick`),h=a.onPrevClick||e.getConfig(`onPrevClick`),g=a.onCloseClick||e.getConfig(`onCloseClick`);return{...i,popover:{showButtons:p,nextBtnText:o?void 0:c,disableButtons:[...s?[]:[`previous`]],showProgress:u,onNextClick:m||n.onNextClick,onPrevClick:h||n.onPrevClick,onCloseClick:g||n.onCloseClick,...a,progressText:d}}}function V(e,t,n){let r=e.getConfig(`stagePadding`)||0;return{side:n.popover?.side||`bottom`,align:n.popover?.align||`start`,offset:r+(e.getConfig(`popoverOffset`)||0),padding:r,centered:t.id===`driver-dummy-element`}}function H(e,t,n){let r=n.popover||{},i=e.getState(`activeIndex`),a=i!==void 0&&I(e,i+1,1)===void 0;return{title:r.title,description:r.description,showButtons:r.showButtons||e.getConfig(`showButtons`),disableButtons:r.disableButtons||e.getConfig(`disableButtons`)||[],showProgress:r.showProgress||e.getConfig(`showProgress`)||!1,progressText:r.progressText??(e.getConfig(`progressText`)||P),nextBtnText:r.nextBtnText??(e.getConfig(`nextBtnText`)||`Next`),prevBtnText:r.prevBtnText??(e.getConfig(`prevBtnText`)||`Previous`),doneButton:a,popoverClass:r.popoverClass||e.getConfig(`popoverClass`)||``,smoothScroll:e.getConfig(`smoothScroll`),onNextClick:()=>{let r=L(e,n);return r?r(t,n,e.getHookOpts()):e.emit(`nextClick`)},onPrevClick:()=>{let r=R(e,n);return r?r(t,n,e.getHookOpts()):e.emit(`prevClick`)},onCloseClick:()=>{let r=z(e,n);return r?r(t,n,e.getHookOpts()):e.emit(`closeClick`)},onRender:t=>{e.setState(`popover`,t),(r.onPopoverRender||e.getConfig(`onPopoverRender`))?.(t,e.getHookOpts())},position:V(e,t,n)}}function U(e,t,n){w(e.getState(`popover`)),S(t,H(e,t,n))}function W(e,t,n){let r=e.getState(`popover`);r&&c(r,t,V(e,t,n))}function G(){let e=document.getElementById(`driver-dummy-element`);if(e)return e;let t=document.createElement(`div`);return t.id=`driver-dummy-element`,t.style.width=`0`,t.style.height=`0`,t.style.pointerEvents=`none`,t.style.opacity=`0`,t.style.position=`fixed`,t.style.top=`50%`,t.style.left=`50%`,document.body.appendChild(t),t}function K(e,t){let n=p(t.element);n||(n=G()),J(e,n,t)}function q(e){let t=e.getState(`__activeElement`),n=e.getState(`__activeStep`);t&&(D(e,t),O(e),W(e,t,n))}function J(e,t,n){let r=e.getConfig(`duration`)||400,i=Date.now(),a=e.getState(`__activeStep`),o=e.getState(`__activeElement`)||t,s=!o||o===t,c=t.id===`driver-dummy-element`,l=o.id===`driver-dummy-element`,u=e.getConfig(`animate`),d=n.onHighlightStarted||e.getConfig(`onHighlightStarted`),f=n?.onHighlighted||e.getConfig(`onHighlighted`),p=a?.onDeselected||e.getConfig(`onDeselected`),h=e.getHookOpts();!s&&p&&p(l?void 0:o,a,h),d&&d(c?void 0:t,n,h);let g=!s&&u,v=!1;x(e.getState(`popover`)),e.setState(`previousStep`,a),e.setState(`previousElement`,o),e.setState(`activeStep`,n),e.setState(`activeElement`,t);let y=()=>{if(e.getState(`__transitionCallback`)!==y)return;let s=Date.now()-i,l=r-s<=r/2;n.popover&&l&&!v&&g&&(U(e,t,n),v=!0),e.getConfig(`animate`)&&s<r?E(e,s,r,o,t):(D(e,t),f&&f(c?void 0:t,n,e.getHookOpts()),e.setState(`__transitionCallback`,void 0),e.setState(`__previousStep`,a),e.setState(`__previousElement`,o),e.setState(`__activeStep`,n),e.setState(`__activeElement`,t)),window.requestAnimationFrame(y)};e.setState(`__transitionCallback`,y),window.requestAnimationFrame(y),_(t,e.getConfig(`smoothScroll`)),!g&&n.popover&&U(e,t,n),document.querySelectorAll(`.driver-active-element-parent`).forEach(e=>{e.classList.remove(`driver-active-element-parent`,`driver-active-element-parent-no-scroll`)}),o.classList.remove(`driver-active-element`,`driver-no-interaction`),o.removeAttribute(`aria-haspopup`),o.removeAttribute(`aria-expanded`),o.removeAttribute(`aria-controls`),(n.disableActiveInteraction??e.getConfig(`disableActiveInteraction`))&&t.classList.add(`driver-no-interaction`);let b=t.parentElement;b&&b!==document.body&&(b.classList.add(`driver-active-element-parent`),m(b)&&b.classList.add(`driver-active-element-parent-no-scroll`)),t.classList.add(`driver-active-element`),t.setAttribute(`aria-haspopup`,`dialog`),t.setAttribute(`aria-expanded`,`true`),t.setAttribute(`aria-controls`,`driver-popover-content`)}function Y(){document.getElementById(`driver-dummy-element`)?.remove(),document.querySelectorAll(`.driver-active-element`).forEach(e=>{let t=e.parentElement;t&&t!==document.body&&t.classList.remove(`driver-active-element-parent`,`driver-active-element-parent-no-scroll`),e.classList.remove(`driver-active-element`,`driver-no-interaction`),e.removeAttribute(`aria-haspopup`),e.removeAttribute(`aria-expanded`),e.removeAttribute(`aria-controls`)})}function X(e){let t=e.getState(`__resizeTimeout`);t&&window.cancelAnimationFrame(t),e.setState(`__resizeTimeout`,window.requestAnimationFrame(()=>q(e)))}function Z(e,t){if(!e.getState(`isInitialized`)||!(t.key===`Tab`||t.keyCode===9))return;let n=e.getState(`__activeElement`),r=e.getState(`popover`)?.wrapper,i=g([...r?[r]:[],...n?[n]:[]]),a=i[0],o=i[i.length-1];t.preventDefault(),t.shiftKey?(i[i.indexOf(document.activeElement)-1]||o)?.focus():(i[i.indexOf(document.activeElement)+1]||a)?.focus()}function Q(e,t){(e.getConfig(`allowKeyboardControl`)??!0)&&(t.key===`Escape`?e.emit(`escapePress`):t.key===`ArrowRight`?e.emit(`arrowRightPress`):t.key===`ArrowLeft`&&e.emit(`arrowLeftPress`))}function te(e,t){let n=e.getState(`__activeElement`),r=t.target;!n||!r||!n.contains(r)||e.emit(`activeElementClick`)}function ne(e){let t=t=>Q(e,t),n=t=>Z(e,t),r=()=>X(e),i=()=>X(e),a=t=>te(e,t);e.setState(`__events`,{onKeyup:t,onKeydown:n,onResize:r,onScroll:i,onClick:a}),window.addEventListener(`keyup`,t,!1),window.addEventListener(`keydown`,n,!1),window.addEventListener(`resize`,r),window.addEventListener(`scroll`,i),document.addEventListener(`click`,a,!1)}function $(e){let t=e.getState(`__events`);t&&(window.removeEventListener(`keyup`,t.onKeyup),window.removeEventListener(`keydown`,t.onKeydown),window.removeEventListener(`resize`,t.onResize),window.removeEventListener(`scroll`,t.onScroll),document.removeEventListener(`click`,t.onClick,!1))}function re(){let e={};function t(t={}){e={animate:!0,duration:400,allowClose:!0,allowScroll:!0,overlayClickBehavior:`close`,overlayOpacity:.7,smoothScroll:!1,disableActiveInteraction:!1,advanceOnClick:!1,skipMissingElement:!1,waitForElement:0,showProgress:!1,stagePadding:10,stageRadius:5,popoverOffset:10,showButtons:[`next`,`previous`,`close`],disableButtons:[],overlayColor:`#000`,...t}}return t(),{getConfig:(t=>t?e[t]:e),configure:t}}function ie(){let e={},t=(t=>t?e[t]:e),n=(t,n)=>{e[t]=n};function r(){e={}}return{getState:t,setState:n,resetState:r}}function ae(){let e={};function t(t,n){e[t]=n}function n(t){e[t]?.()}function r(){e={}}return{listen:t,emit:n,reset:r}}function oe(e={}){let t=re();t.configure(e);let n=ie(),r=ae(),i;return{getConfig:t.getConfig,setConfig:t.configure,getState:n.getState,setState:n.setState,resetState:n.resetState,listen:r.listen,emit:r.emit,resetEmitter:r.reset,getDriver:()=>i,setDriver:e=>{i=e},getHookOpts:e=>{let r=e||n.getState();return{config:t.getConfig(),state:r,driver:i,index:r.activeIndex}}}}function se(e={}){let t=oe(e);function n(){t.getConfig(`allowClose`)&&h()}function r(){let e=t.getConfig(`overlayClickBehavior`);if(t.getConfig(`allowClose`)&&e===`close`){h();return}if(typeof e==`function`){let n=t.getState(`__activeStep`);e(t.getState(`__activeElement`),n,t.getHookOpts());return}if(e===`nextStep`){let e=t.getState(`activeStep`),n=t.getState(`activeElement`),r=L(t,e);if(r){r(n,e,t.getHookOpts());return}i()}}function i(){let e=t.getState(`activeIndex`),n=t.getConfig(`steps`)||[];if(e===void 0)return;let r=e+1;n[r]?m(r):h()}function a(){let e=t.getState(`activeIndex`),n=t.getConfig(`steps`)||[];if(e===void 0)return;let r=e-1;n[r]?m(r):h()}function o(e){(t.getConfig(`steps`)||[])[e]?m(e):h()}function s(){if(t.getState(`__transitionCallback`))return;let e=t.getState(`__activeStep`);if(!e||!(e.advanceOnClick??t.getConfig(`advanceOnClick`)))return;let n=t.getState(`__activeElement`),r=L(t,e);if(r){r(n,e,t.getHookOpts());return}i()}function c(){if(t.getState(`__transitionCallback`))return;let e=t.getState(`activeIndex`),n=t.getState(`__activeStep`),r=t.getState(`__activeElement`);if(e===void 0||n===void 0||!(t.getConfig(`steps`)||[])[e-1])return;let i=R(t,n);if(i)return i(r,n,t.getHookOpts());a()}function l(){if(t.getState(`__transitionCallback`))return;let e=t.getState(`activeIndex`),n=t.getState(`__activeStep`),r=t.getState(`__activeElement`);if(e===void 0||n===void 0)return;let a=L(t,n);if(a)return a(r,n,t.getHookOpts());i()}function u(){t.getState(`isInitialized`)||(t.setState(`isInitialized`,!0),document.body.classList.add(`driver-active`,t.getConfig(`animate`)?`driver-fade`:`driver-simple`),t.getConfig(`allowScroll`)||document.body.classList.add(`driver-no-scroll`),document.body.style.setProperty(`--driver-animation-duration`,`${t.getConfig(`duration`)||400}ms`),ne(t),t.listen(`overlayClick`,r),t.listen(`activeElementClick`,s),t.listen(`escapePress`,n),t.listen(`closeClick`,n),t.listen(`arrowLeftPress`,c),t.listen(`arrowRightPress`,l))}function d(){let e=t.getState(`__pendingWaitCancel`);e&&(t.setState(`__pendingWaitCancel`,void 0),e())}function f(e,n,r){let i=()=>{a.disconnect(),window.clearTimeout(o),t.setState(`__pendingWaitCancel`,void 0),r()},a=new MutationObserver(()=>{p(e.element)&&i()}),o=window.setTimeout(i,n);t.setState(`__pendingWaitCancel`,()=>{a.disconnect(),window.clearTimeout(o)}),a.observe(document.documentElement,{childList:!0,subtree:!0,attributes:!0})}function m(e=0,n=!1){d();let r=t.getConfig(`steps`);if(!r){console.error(`No steps to drive through`),h();return}if(!r[e]){h();return}let i=r[e],a=i.waitForElement??t.getConfig(`waitForElement`)??0;if(!n&&a>0&&i.element&&!p(i.element)){f(i,a,()=>m(e,!0));return}if(F(t,i)){let n=t.getState(`activeIndex`),i=typeof n==`number`&&e<n?-1:1;r[e+i]?m(e+i):i===1&&h();return}t.setState(`__activeOnDestroyed`,document.activeElement),t.setState(`activeIndex`,e);let o=r[e+1];K(t,B(t,e,{onNextClick:()=>{o?m(e+1):h()},onPrevClick:()=>{m(e-1)},onCloseClick:()=>{h()}}))}function h(e=!0){let n=t.getState(`__activeElement`),r=t.getState(`__activeStep`),i=t.getState(`__activeOnDestroyed`),a=t.getConfig(`onDestroyStarted`);if(e&&a){a(!n||n?.id===`driver-dummy-element`?void 0:n,r,t.getHookOpts());return}let o=r?.onDeselected||t.getConfig(`onDeselected`),s=t.getConfig(`onDestroyed`);document.body.classList.remove(`driver-active`,`driver-fade`,`driver-simple`,`driver-no-scroll`),document.body.style.removeProperty(`--driver-animation-duration`),d(),$(t),w(t.getState(`popover`)),Y(),N(t),t.resetEmitter();let c=t.getState();if(t.resetState(),n&&r){let e=n.id===`driver-dummy-element`;o&&o(e?void 0:n,r,t.getHookOpts(c)),s&&s(e?void 0:n,r,t.getHookOpts(c))}i&&i.focus()}let g={isActive:()=>t.getState(`isInitialized`)||!1,refresh:()=>X(t),drive:(e=0)=>{u(),m(e)},setConfig:t.setConfig,setSteps:e=>{d(),t.resetState(),t.setConfig({...t.getConfig(),steps:e})},getConfig:t.getConfig,getState:t.getState,getActiveIndex:()=>t.getState(`activeIndex`),isFirstStep:()=>{let e=t.getState(`activeIndex`);return e!==void 0&&I(t,e-1,-1)===void 0},isLastStep:()=>{let e=t.getState(`activeIndex`);return e!==void 0&&I(t,e+1,1)===void 0},getActiveStep:()=>t.getState(`activeStep`),getActiveElement:()=>t.getState(`activeElement`),getPreviousElement:()=>t.getState(`previousElement`),getPreviousStep:()=>t.getState(`previousStep`),getNextStep:()=>{let e=t.getConfig(`steps`)||[],n=t.getState(`activeIndex`);if(n===void 0)return;let r=I(t,n+1,1);return r===void 0?void 0:e[r]},moveNext:i,movePrevious:a,moveTo:o,hasNextStep:()=>{let e=t.getState(`activeIndex`);return e!==void 0&&I(t,e+1,1)!==void 0},hasPreviousStep:()=>{let e=t.getState(`activeIndex`);return e!==void 0&&I(t,e-1,-1)!==void 0},highlight:e=>{u(),K(t,{...e,popover:e.popover?{showButtons:[],showProgress:!1,progressText:``,...e.popover}:void 0})},destroy:()=>{h(!1)}};return t.setDriver(g),g}return e.driver=se,e})({});
/* ===== vendor: driver.css，內嵌成字串常數給 overlay.src.js 注入 ===== */
var __SHOWME_DRIVER_CSS__ = ".driver-popover{all:unset;font-family:var(--driver-popover-font-family,\"Helvetica Neue\", Inter, ui-sans-serif, \"Apple Color Emoji\", Helvetica, Arial, sans-serif);box-sizing:border-box;color:#2d2d2d;z-index:1000000000;background-color:#fff;border-radius:5px;min-width:250px;max-width:300px;margin:0;padding:15px;position:fixed;top:0;right:0;box-shadow:0 1px 10px #0006}.driver-popover-title{zoom:1;margin:0;font-size:19px;font-weight:700;line-height:1.5;display:block;position:relative}.driver-popover-close-btn{all:unset;cursor:pointer;color:#d2d2d2;z-index:1;text-align:center;width:32px;height:28px;font-size:18px;font-weight:500;transition:color .2s;position:absolute;top:0;right:0}.driver-popover-close-btn:hover,.driver-popover-close-btn:focus{color:#2d2d2d}.driver-popover-title[style*=block]+.driver-popover-description{margin-top:5px}.driver-popover-description{zoom:1;margin-bottom:0;font-size:14px;font-weight:400;line-height:1.5}.driver-popover-footer{text-align:right;zoom:1;justify-content:space-between;align-items:center;margin-top:15px;display:flex}.driver-popover-progress-text{color:#727272;zoom:1;font-size:13px;font-weight:400}.driver-popover-footer-btn{all:unset;box-sizing:border-box;color:#2d2d2d;cursor:pointer;zoom:1;background-color:#fff;border:1px solid #ccc;border-radius:3px;outline:0;padding:3px 7px;font-size:12px;line-height:1.3;text-decoration:none;display:inline-block}.driver-popover-footer .driver-popover-btn-disabled{opacity:.5;pointer-events:none}.driver-popover-footer-btn:hover,.driver-popover-footer-btn:focus{background-color:#f7f7f7}.driver-popover-navigation-btns{flex-grow:1;justify-content:flex-end;display:flex}.driver-popover-navigation-btns button+button{margin-left:4px}.driver-popover-arrow{content:\"\";border:5px solid #fff;position:absolute}.driver-popover-arrow-side-over{display:none}.driver-popover-arrow-side-left{border-top-color:#0000;border-bottom-color:#0000;border-right-color:#0000;left:100%}.driver-popover-arrow-side-right{border-top-color:#0000;border-bottom-color:#0000;border-left-color:#0000;right:100%}.driver-popover-arrow-side-top{border-bottom-color:#0000;border-left-color:#0000;border-right-color:#0000;top:100%}.driver-popover-arrow-side-bottom{border-top-color:#0000;border-left-color:#0000;border-right-color:#0000;bottom:100%}.driver-popover-arrow-side-center,.driver-popover-arrow-none{display:none}.driver-active .driver-overlay{pointer-events:none}.driver-active.driver-no-scroll{overflow:hidden}.driver-active *{pointer-events:none}.driver-active .driver-active-element,.driver-active .driver-active-element *,.driver-popover,.driver-popover *{pointer-events:auto}@keyframes animate-fade-in{0%{opacity:0}to{opacity:1}}.driver-fade .driver-overlay{animation:animate-fade-in var(--driver-animation-duration,.4s) ease-in-out}.driver-fade .driver-popover{animation:animate-fade-in var(--driver-animation-duration,.4s)}.driver-active-element-parent-no-scroll{overflow:hidden!important}.driver-no-interaction,.driver-no-interaction *{pointer-events:none!important}\n";

/* ===== ShowMe overlay 邏輯（來源：overlay/overlay.src.js） ===== */
/*
 * ShowMe overlay — 人員 B 負責。
 *
 * 這份檔案不是直接注入的檔案：build.sh 會把它跟 vendor/driver.iife.js、
 * vendor/driver.css 串成 overlay/dist/overlay.bundle.js，人員 A 用
 * `context.add_init_script(path="overlay/dist/overlay.bundle.js")` 注入一個檔案。
 *
 * 對外只暴露 window.__showme = { snapshot, show, clear, done }，
 * 以及會呼叫 window.__showme_emit({ kind, url, ts, signal })（由人員 A 的
 * page.expose_function 提供，此檔不負責定義它）。
 *
 * 目前進度（S3）：snapshot() 已實作、可獨立測試。
 * show / observe / clear / done 是 S4 待做，先留 stub 不讓呼叫直接炸掉。
 * 對應規格：docs/design/showme.md §10（snapshot/uid）、§11（完成判定）、§12（介面）。
 */
(function () {
  "use strict";

  // 已經注入過就不要重複安裝（例如同一頁被重複 add_init_script 兩次）。
  if (window.__showme) {
    return;
  }

  // ---------------------------------------------------------------------
  // 角色白名單（docs/design/showme.md §10）：
  // button、link、textbox、checkbox、radio、combobox、menuitem、tab、
  // heading、alert。
  //
  // 每個角色一組 CSS selector；全部合併成一個 selector 字串後只呼叫一次
  // querySelectorAll —— DOM 規範保證回傳結果依 tree order 排列，且同一個
  // 元素就算同時符合多個子 selector 也只會出現一次，天然去重、天然照 DOM 序。
  // ---------------------------------------------------------------------
  var ROLE_SELECTORS = {
    button:
      'button, input[type="button"], input[type="submit"], input[type="reset"], [role="button"]',
    link: 'a[href], [role="link"]',
    textbox:
      'input:not([type]), input[type="text"], input[type="search"], ' +
      'input[type="email"], input[type="url"], input[type="tel"], ' +
      'input[type="password"], input[type="number"], textarea, ' +
      '[role="textbox"], [contenteditable="true"], [contenteditable=""]',
    checkbox: 'input[type="checkbox"], [role="checkbox"]',
    radio: 'input[type="radio"], [role="radio"]',
    combobox: 'select, [role="combobox"]',
    menuitem: '[role="menuitem"]',
    tab: '[role="tab"]',
    heading: 'h1, h2, h3, h4, h5, h6, [role="heading"]',
    alert: '[role="alert"]',
  };

  // 顯性 role="..." 覆蓋原生標籤語意時的優先序（ARIA 精神：作者指定的 role 優先）。
  var EXPLICIT_ROLE_WHITELIST = Object.keys(ROLE_SELECTORS);

  var ALL_SELECTOR = Object.keys(ROLE_SELECTORS)
    .map(function (k) {
      return ROLE_SELECTORS[k];
    })
    .join(", ");

  var MAX_ELEMENTS = 150;

  // 原生標籤 → 角色 的 fallback 表（沒有顯性 role 屬性時用這個判斷）。
  function nativeRoleOf(el) {
    var tag = el.tagName.toLowerCase();
    if (tag === "button") return "button";
    if (tag === "a" && el.hasAttribute("href")) return "link";
    if (tag === "select") return "combobox";
    if (tag === "textarea") return "textbox";
    if (/^h[1-6]$/.test(tag)) return "heading";
    if (tag === "input") {
      var type = (el.getAttribute("type") || "text").toLowerCase();
      if (type === "button" || type === "submit" || type === "reset") return "button";
      if (type === "checkbox") return "checkbox";
      if (type === "radio") return "radio";
      // text/search/email/url/tel/password/number/沒填 type 都算 textbox
      return "textbox";
    }
    if (el.hasAttribute("contenteditable")) {
      var ce = el.getAttribute("contenteditable").toLowerCase();
      if (ce === "true" || ce === "") return "textbox";
    }
    return null;
  }

  function roleOf(el) {
    var explicit = (el.getAttribute("role") || "").toLowerCase();
    if (explicit && EXPLICIT_ROLE_WHITELIST.indexOf(explicit) !== -1) {
      return explicit;
    }
    return nativeRoleOf(el) || explicit || "";
  }

  // ---------------------------------------------------------------------
  // 簡化版 accessible name：不是完整 W3C accname 演算法，但涵蓋一般表單/
  // 按鈕會用到的來源，順序大致照官方演算法的優先序。沒有就回傳 ""
  // （spec 明講：沒有 a11y name，name 為空字串，元素仍要列出）。
  // ---------------------------------------------------------------------
  function collapse(s) {
    return (s || "").replace(/\s+/g, " ").trim();
  }

  function labelFor(el) {
    if (el.id) {
      var byFor = document.querySelector('label[for="' + cssEscape(el.id) + '"]');
      if (byFor) return collapse(byFor.textContent);
    }
    var wrapping = el.closest ? el.closest("label") : null;
    if (wrapping) return collapse(wrapping.textContent);
    return "";
  }

  function cssEscape(s) {
    if (window.CSS && CSS.escape) return CSS.escape(s);
    return String(s).replace(/[^a-zA-Z0-9_-]/g, "\\$&");
  }

  function accessibleName(el) {
    var ariaLabel = collapse(el.getAttribute("aria-label"));
    if (ariaLabel) return ariaLabel;

    var labelledBy = el.getAttribute("aria-labelledby");
    if (labelledBy) {
      var text = labelledBy
        .split(/\s+/)
        .map(function (id) {
          var ref = document.getElementById(id);
          return ref ? collapse(ref.textContent) : "";
        })
        .filter(Boolean)
        .join(" ");
      if (text) return collapse(text);
    }

    var label = labelFor(el);
    if (label) return label;

    var tag = el.tagName.toLowerCase();
    if (tag === "input") {
      var type = (el.getAttribute("type") || "text").toLowerCase();
      if (type === "button" || type === "submit" || type === "reset") {
        var v = collapse(el.getAttribute("value"));
        if (v) return v;
      }
    }
    if (tag === "input" || tag === "textarea") {
      var placeholder = collapse(el.getAttribute("placeholder"));
      if (placeholder) return placeholder;
    }

    var text = collapse(el.textContent);
    if (text) return text;

    var img = el.querySelector ? el.querySelector("img[alt]") : null;
    if (img) {
      var alt = collapse(img.getAttribute("alt"));
      if (alt) return alt;
    }

    var title = collapse(el.getAttribute("title"));
    if (title) return title;

    return "";
  }

  // ---------------------------------------------------------------------
  // snapshot(n) → { elements, truncated }
  // ---------------------------------------------------------------------
  function snapshot(snapshotNumber) {
    var all = document.querySelectorAll(ALL_SELECTOR);
    var truncated = all.length > MAX_ELEMENTS;
    var limited = Array.prototype.slice.call(all, 0, MAX_ELEMENTS);

    var elements = limited.map(function (el, i) {
      var uid = "s" + snapshotNumber + "-" + (i + 1);
      el.setAttribute("data-showme-uid", uid);
      return {
        uid: uid,
        role: roleOf(el),
        name: accessibleName(el),
        testid: el.getAttribute("data-testid") || "",
      };
    });

    return { elements: elements, truncated: truncated };
  }

  // ---------------------------------------------------------------------
  // emit：唯一跟 Python 講話的管道。__showme_emit 由人員 A 的
  // page.expose_function 提供，這份檔案不負責定義它。
  // ---------------------------------------------------------------------
  function emit(kind, extra) {
    var payload = Object.assign(
      { kind: kind, url: location.href, ts: Date.now() },
      extra || {}
    );
    if (typeof window.__showme_emit === "function") {
      window.__showme_emit(payload);
    } else {
      console.warn("[showme] __showme_emit 不存在（在 Playwright 外測試？）", payload);
    }
  }

  // ---------------------------------------------------------------------
  // history.pushState / replaceState 只包一次；popstate、hashchange 一起轉成
  // 同一個自訂事件，observe(kind="click") 用它判斷 URL 變了沒（§11）。
  // ---------------------------------------------------------------------
  var historyPatched = false;
  function patchHistoryOnce() {
    if (historyPatched) return;
    historyPatched = true;

    function fireLocationChange() {
      window.dispatchEvent(new Event("showme:locationchange"));
    }

    var rawPush = history.pushState;
    var rawReplace = history.replaceState;
    history.pushState = function () {
      var ret = rawPush.apply(this, arguments);
      fireLocationChange();
      return ret;
    };
    history.replaceState = function () {
      var ret = rawReplace.apply(this, arguments);
      fireLocationChange();
      return ret;
    };
    window.addEventListener("popstate", fireLocationChange);
    window.addEventListener("hashchange", fireLocationChange);
  }

  // driver.css 由 build.sh 內嵌成 __SHOWME_DRIVER_CSS__（沒 vendor 進來時這個
  // 識別字根本不存在——用 typeof 判斷才不會直接 ReferenceError）。
  var driverCssInjected = false;
  function injectDriverCssOnce() {
    if (driverCssInjected) return;
    driverCssInjected = true;
    if (typeof __SHOWME_DRIVER_CSS__ === "undefined") {
      console.error(
        "[showme] driver.css 沒有內嵌進來：確認 overlay/vendor/driver.css 存在，且是跑 " +
          "./build.sh 產生的 overlay.js，不是直接載入 overlay.src.js。"
      );
      return;
    }
    var style = document.createElement("style");
    style.setAttribute("data-showme", "driver-css");
    style.textContent = __SHOWME_DRIVER_CSS__;
    (document.head || document.documentElement).appendChild(style);
  }

  // 「隱藏」的最小集合定義（§11 design，非像素級）：
  // 不在 document 裡、display:none、visibility:hidden、aria-hidden=true。
  function isGone(el) {
    if (!el.isConnected) return true;
    var style = window.getComputedStyle(el);
    if (style.display === "none" || style.visibility === "hidden") return true;
    if (el.getAttribute("aria-hidden") === "true") return true;
    return false;
  }

  // rAF 內合併同一畫面內的多次 mutation callback，避免對每個 mutation 都重算一次
  // getComputedStyle／innerText——這只是節流，不是「數 mutation 次數」判完成。
  function rafDebounce(fn) {
    var scheduled = false;
    return function () {
      if (scheduled) return;
      scheduled = true;
      requestAnimationFrame(function () {
        scheduled = false;
        fn();
      });
    };
  }

  // ---------------------------------------------------------------------
  // 進行中那一步的狀態。同一時間最多一份；每份只准 emit 一次（finish 的 guard）。
  // ---------------------------------------------------------------------
  var current = null;

  function teardown() {
    if (!current) return;
    var c = current;
    current = null;
    c.cleanupFns.forEach(function (fn) {
      try {
        fn();
      } catch (e) {
        console.error("[showme] teardown 清理失敗", e);
      }
    });
    if (c.driverInstance) {
      try {
        c.driverInstance.destroy();
      } catch (e) {
        console.error("[showme] driver destroy 失敗", e);
      }
    }
  }

  function finish(kind, signal) {
    if (!current || current.emitted) return;
    current.emitted = true;
    var uid = current.uid;
    teardown();
    emit(kind, { signal: signal, uid: uid });
  }

  // ---------------------------------------------------------------------
  // observe(kind, el, expectText)：依 kind 掛完成條件的 listener，全部塞進
  // current.cleanupFns，讓 teardown() 統一拆。任何 kind 共同的 Next／I'm stuck
  // 不在這裡處理，是 show() 掛在 Driver.js popover 按鈕上。
  // ---------------------------------------------------------------------
  function observe(kind, el, expectText) {
    if (kind === "click") {
      var startUrl = location.href;

      var checkGone = rafDebounce(function () {
        if (isGone(el)) finish("step_done", "removed_or_hidden");
      });
      var mo = new MutationObserver(checkGone);
      mo.observe(document.documentElement, {
        subtree: true,
        childList: true,
        attributes: true,
        attributeFilter: ["style", "class", "aria-hidden", "hidden"],
      });
      current.cleanupFns.push(function () {
        mo.disconnect();
      });

      function onLocationChange() {
        if (location.href !== startUrl) finish("step_done", "url_changed");
      }
      window.addEventListener("showme:locationchange", onLocationChange);
      current.cleanupFns.push(function () {
        window.removeEventListener("showme:locationchange", onLocationChange);
      });
      return;
    }

    if (kind === "input") {
      function onInputSignal(e) {
        if ((el.value || "").length > 0) finish("step_done", e.type);
      }
      el.addEventListener("blur", onInputSignal);
      el.addEventListener("change", onInputSignal);
      current.cleanupFns.push(function () {
        el.removeEventListener("blur", onInputSignal);
        el.removeEventListener("change", onInputSignal);
      });
      return;
    }

    if (kind === "select") {
      function onChange() {
        finish("step_done", "change");
      }
      el.addEventListener("change", onChange);
      current.cleanupFns.push(function () {
        el.removeEventListener("change", onChange);
      });
      return;
    }

    // observe，以及不合法 kind 一律落到這裡（T 層已轉成 observe，這裡只管完成條件）。
    if (!expectText) {
      // Python 應該已經擋掉空 expect_text 才會呼叫 show；防禦性處理，不掛 observer。
      return;
    }
    var checkText = rafDebounce(function () {
      var body = document.body ? document.body.innerText : "";
      if (body.indexOf(expectText) !== -1) finish("step_done", "expect_text");
    });
    var textMo = new MutationObserver(checkText);
    textMo.observe(document.body, { childList: true, subtree: true, characterData: true });
    current.cleanupFns.push(function () {
      textMo.disconnect();
    });
    // 立即檢查一次：expect_text 有可能在開始觀察的當下就已經在畫面上。
    var body0 = document.body ? document.body.innerText : "";
    if (body0.indexOf(expectText) !== -1) finish("step_done", "expect_text");
  }

  // ---------------------------------------------------------------------
  // show({uid, instruction, kind, index, total, expect})
  // ---------------------------------------------------------------------
  var VALID_KINDS = ["click", "input", "select", "observe"];

  function show(opts) {
    teardown(); // 上一步如果還沒收尾（理論上 A 會先等 finish 才叫下一次 show），先清乾淨、不 emit

    var uid = opts.uid;
    var kind = VALID_KINDS.indexOf(opts.kind) !== -1 ? opts.kind : "observe";
    var expect = opts.expect || "";

    var el = document.querySelector('[data-showme-uid="' + cssEscape(uid) + '"]');
    if (!el) {
      console.error("[showme] show(): 找不到 uid 對應的元素", uid);
      return;
    }

    injectDriverCssOnce();
    patchHistoryOnce();

    if (typeof el.scrollIntoView === "function") {
      el.scrollIntoView({ block: "center", behavior: "instant" });
    }

    current = { uid: uid, emitted: false, cleanupFns: [], driverInstance: null };

    var driverFactory =
      window.driver && window.driver.js && window.driver.js.driver;
    if (typeof driverFactory !== "function") {
      console.error(
        "[showme] Driver.js 沒有載入：確認 overlay/vendor/driver.iife.js 存在，且是跑 " +
          "./build.sh 產生的 overlay.js。沒有高亮還是繼續判斷完成條件，不然會整個卡死。"
      );
      observe(kind, el, expect);
      return;
    }

    var driverObj = driverFactory({
      animate: true,
      allowClose: false,
      overlayOpacity: 0.5,
      stagePadding: 6,
      popoverClass: "showme-popover",
    });
    current.driverInstance = driverObj;

    driverObj.highlight({
      element: el,
      popover: {
        title: "Step " + opts.index + " / " + opts.total,
        description: opts.instruction || "",
        showButtons: ["next"],
        nextBtnText: "Next",
        onNextClick: function () {
          finish("step_done", "next_button");
        },
        onPopoverRender: function (popover) {
          var stuckBtn = document.createElement("button");
          stuckBtn.type = "button";
          stuckBtn.textContent = "I'm stuck";
          stuckBtn.className = "driver-popover-footer-btn showme-stuck-btn";
          stuckBtn.style.marginLeft = "8px";
          stuckBtn.addEventListener("click", function () {
            finish("stuck", "stuck_button");
          });
          popover.footerButtons.appendChild(stuckBtn);
        },
      },
    });

    observe(kind, el, expect);
  }

  // ---------------------------------------------------------------------
  // clear() / done(text)
  // ---------------------------------------------------------------------
  var BANNER_ID = "__showme-banner";

  function removeBanner() {
    var el = document.getElementById(BANNER_ID);
    if (el) el.remove();
  }

  function showBanner(text) {
    removeBanner();
    var el = document.createElement("div");
    el.id = BANNER_ID;
    el.textContent = text;
    el.style.cssText = [
      "position:fixed",
      "top:16px",
      "left:50%",
      "transform:translateX(-50%)",
      "z-index:2147483647",
      "background:#16a34a",
      "color:#fff",
      "font:600 15px/1.4 system-ui,sans-serif",
      "padding:10px 20px",
      "border-radius:8px",
      "box-shadow:0 4px 16px rgba(0,0,0,.25)",
    ].join(";");
    document.body.appendChild(el);
  }

  function clear() {
    teardown();
    removeBanner();
  }

  function done(text) {
    teardown();
    showBanner(text);
  }

  window.__showme = {
    snapshot: snapshot,
    show: show,
    clear: clear,
    done: done,
  };
})();
