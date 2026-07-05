export function PlaceholderPage({ title }: { title: string }) {
  return (
    <div className="p-6">
      <h1 className="text-lg font-semibold">{title}</h1>
      <p className="mt-2 text-sm text-muted-foreground">이 기능은 다음 단계에서 구현됩니다.</p>
    </div>
  )
}
