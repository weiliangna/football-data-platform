export function esc(value: unknown): string {
  return String(value ?? '')
    .replaceAll('&','&amp;')
    .replaceAll('<','&lt;')
    .replaceAll('>','&gt;')
    .replaceAll('"','&quot;')
    .replaceAll("'",'&#39;');
}
export function qs<T extends Element=HTMLElement>(selector:string,root:ParentNode=document):T|null{return root.querySelector(selector) as T|null}
export function qsa<T extends Element=HTMLElement>(selector:string,root:ParentNode=document):T[]{return [...root.querySelectorAll(selector)] as T[]}
export function on(selector:string,event:string,handler:(el:HTMLElement,e:Event)=>void,root:ParentNode=document){qsa<HTMLElement>(selector,root).forEach(el=>el.addEventListener(event,e=>handler(el,e)))}
export function toast(message:string){const el=document.createElement('div');el.className='toast';el.textContent=message;document.body.appendChild(el);setTimeout(()=>el.remove(),1600)}
