import { cn } from '../../lib/utils'

export default function SettingsSection({ title, description, children, danger = false }) {
  return (
    <section className={cn(
      "rounded-xl p-5 glass",
      danger ? "border-red-500/20 bg-red-500/5" : ""
    )}>
      <header className="mb-4">
        <h3 className={cn(
          "text-base font-semibold",
          danger ? "text-red-400" : "text-foreground"
        )}>
          {title}
        </h3>
        {description ? (
          <p className="mt-1 text-sm text-muted-foreground">{description}</p>
        ) : null}
      </header>
      <div className="space-y-4">{children}</div>
    </section>
  )
}