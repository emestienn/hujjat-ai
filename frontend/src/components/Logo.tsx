export function Logo() {
  return (
    <div className="flex items-center gap-2.5">
      <img src="/favicon.svg" alt="" className="size-9 rounded-xl shadow-lg shadow-iris/20" />
      <div className="leading-tight">
        <p className="text-[15px] font-extrabold tracking-tight text-white">
          Hujjat <span className="brand-text">AI</span>
        </p>
        <p className="text-[11px] text-zinc-500">Chat with your documents</p>
      </div>
    </div>
  )
}
