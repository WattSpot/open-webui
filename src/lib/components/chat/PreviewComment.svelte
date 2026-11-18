<script lang="ts">
	import type { PreviewSelection } from '$lib/utils/previewAnnotations';
	export let note: PreviewSelection & { comment: string };
	$: path = new URL(note.url).pathname;
	$: excerpt = (note.label || note.text || note.role || note.tag).replace(/\s+/g, ' ').trim();
</script>

<div class="min-w-0 space-y-1 py-1 text-start">
	<p class="truncate text-xs text-gray-600 dark:text-gray-300">
		{path === '/' ? 'Homepage' : path} · {excerpt.length > 56
			? excerpt.slice(0, 55) + '…'
			: excerpt}
	</p>
	<p class="whitespace-pre-wrap break-words">{note.comment}</p>
	<details class="text-xs text-gray-600 dark:text-gray-300">
		<summary class="w-fit cursor-pointer">Details</summary>
		<dl class="mt-2 grid gap-1.5 [overflow-wrap:anywhere]">
			<div>
				<dt>Selector</dt>
				<dd><code>{note.selector}</code></dd>
			</div>
			<div>
				<dt>URL</dt>
				<dd>{note.url}</dd>
			</div>
			<div>
				<dt>Checkout</dt>
				<dd><code>{note.root}</code></dd>
			</div>
			<div>
				<dt>Element</dt>
				<dd>{note.tag}{note.role ? ` · ${note.role}` : ''}</dd>
			</div>
			{#if note.label}<div>
					<dt>Label</dt>
					<dd>{note.label}</dd>
				</div>{/if}
			{#if note.text}<div>
					<dt>Selected text</dt>
					<dd>{note.text}</dd>
				</div>{/if}
		</dl>
	</details>
</div>
