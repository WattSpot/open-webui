<script lang="ts">
	import { onDestroy, tick } from 'svelte';
	import ChatBubble from '$lib/components/icons/ChatBubble.svelte';
	import EllipsisHorizontal from '$lib/components/icons/EllipsisHorizontal.svelte';
	import XMark from '$lib/components/icons/XMark.svelte';
	import {
		terminalRequest,
		type TerminalConnection,
		type TerminalProcessOutput
	} from '$lib/apis/terminal';
	import {
		previewSelection,
		type Preview,
		type PreviewSelection
	} from '$lib/utils/previewAnnotations';
	export let preview: Preview;
	export let active: boolean;
	export let connection: TerminalConnection;
	export let chatId: string | null;
	export let directory: string;
	let starting = false;
	let startError = '';
	const controller = new AbortController();
	onDestroy(() => controller.abort());

	async function startPreview() {
		const target =
			preview.id === 'website'
				? ['website:dev', 14321]
				: preview.id === 'app'
					? ['ws-app:dev', 5174]
					: null;
		if (!target || starting) return;
		starting = true;
		startError = '';
		try {
			const { signal } = controller;
			let result = await terminalRequest<TerminalProcessOutput>(
				connection,
				chatId,
				'/execute?wait=1&tail=30',
				{
					method: 'POST',
					headers: { 'Content-Type': 'application/json' },
					signal,
					body: JSON.stringify({
						command: `corepack pnpm run ${target[0]}`,
						cwd: directory,
						env: { NO_COLOR: '1' }
					})
				}
			);
			const deadline = Date.now() + 60000;
			while (true) {
				const output = result.output.map((entry) => entry.data).join('');
				if (result.status !== 'running')
					throw new Error(output.trim() || 'Preview command exited.');
				// Both Astro and Vite print their local URL once the server is listening.
				if (
					['localhost', '127.0.0.1'].some((host) => output.includes(`http://${host}:${target[1]}/`))
				) {
					frame.src = preview.url;
					break;
				}
				if (Date.now() >= deadline)
					throw new Error(
						'Still waiting for the preview URL. Check the terminal output, then reload.'
					);
				result = await terminalRequest<TerminalProcessOutput>(
					connection,
					chatId,
					`/execute/${encodeURIComponent(result.id)}/status?wait=1&tail=30`,
					{ signal }
				);
			}
		} catch (error) {
			if (!controller.signal.aborted)
				startError = error instanceof Error ? error.message : String(error);
		} finally {
			starting = false;
		}
	}
	export let onAnnotate: (selection: PreviewSelection, comment: string) => boolean;
	let frame: HTMLIFrameElement;
	let nonce = '';
	let ready = false;
	let picking = false;
	let selection: PreviewSelection | null = null;
	let comment = '';
	let anchor: { x: number; y: number } | null = null;
	let launcher: HTMLButtonElement;
	let input: HTMLTextAreaElement;
	let panelHeight = 0;
	let cardHeight = 152;
	async function dismiss() {
		selection = null;
		comment = '';
		picking = false;
		send('cancel');
		await tick();
		launcher?.focus();
	}
	function saveComment() {
		if (selection && comment.trim() && onAnnotate(selection, comment.trim())) void dismiss();
	}
	function shortcut(event: KeyboardEvent) {
		if (!active || event.isComposing) return;
		if (event.key === 'Escape' && (selection || picking)) {
			event.preventDefault();
			void dismiss();
		} else if (selection && (event.metaKey || event.ctrlKey) && event.key === 'Enter') {
			event.preventDefault();
			saveComment();
		}
	}
	$: origin = new URL(preview.url).origin;
	const send = (action: string) =>
		frame?.contentWindow?.postMessage(
			{ type: 'open-webui-preview', version: 1, nonce, action },
			origin
		);
	const connect = () => {
		nonce = crypto.randomUUID();
		ready = false;
		picking = false;
		selection = null;
		send('connect');
	};
	$: if (!active) {
		picking = false;
		selection = null;
		comment = '';
		send('cancel');
	}
	const receive = (event: MessageEvent) => {
		if (event.source !== frame?.contentWindow || event.origin !== origin) return;
		const data = event.data;
		if (data?.type !== 'open-webui-preview' || data.version !== 1 || data.nonce !== nonce) return;
		if (data.action === 'ready') {
			ready = true;
			startError = '';
		}
		if (!active) return;
		if (data.action === 'cancel' && picking) void dismiss();
		if (data.action === 'selection' && picking) {
			selection = previewSelection(data.selection, origin);
			anchor = Number.isFinite(data.point?.x) && Number.isFinite(data.point?.y) ? data.point : null;
			comment = '';
			if (selection) void tick().then(() => input?.focus());
			picking = false;
		}
	};
</script>

<svelte:window on:message={receive} on:keydown={shortcut} />
<div
	class="stage relative h-full w-full overflow-hidden bg-white dark:bg-gray-900"
	bind:clientHeight={panelHeight}
>
	<iframe
		bind:this={frame}
		src={preview.url}
		title={`${preview.label} preview`}
		class="absolute inset-0 h-full w-full border-0"
		on:load={connect}
		sandbox="allow-scripts allow-same-origin allow-forms allow-popups allow-popups-to-escape-sandbox allow-downloads"
	></iframe>
	{#if selection}
		<div class="absolute inset-0" role="presentation">
			{#if anchor}<span
					class="pin"
					aria-hidden="true"
					style:left={`${anchor.x}px`}
					style:top={`${anchor.y}px`}
				></span>{/if}
			<form
				class="card surface"
				aria-label="Element comment"
				bind:clientHeight={cardHeight}
				style:left={anchor
					? `clamp(8px, ${anchor.x + 12}px, calc(100% - var(--card-width) - 8px))`
					: undefined}
				style:top={anchor
					? `clamp(8px, ${anchor.y + cardHeight + 24 < panelHeight ? anchor.y + 12 : anchor.y - cardHeight - 14}px, calc(100% - ${cardHeight + 10}px))`
					: undefined}
				class:fallback={!anchor}
				on:submit|preventDefault={saveComment}
			>
				<div class="flex items-center gap-2 text-xs">
					<code class="element-tag">{selection.tag}</code>
					<span class="min-w-0 flex-1 truncate text-gray-600 dark:text-gray-300"
						>{selection.label || selection.text}</span
					>
					<button type="button" aria-label="Cancel comment" class="icon-button" on:click={dismiss}
						><XMark /></button
					>
				</div>
				<textarea
					bind:this={input}
					bind:value={comment}
					aria-label="Comment"
					placeholder="Add a comment…"
					maxlength="2000"
					rows="2"
					required
				></textarea>
				<div class="flex justify-end">
					<button class="add" disabled={!comment.trim()}>Add annotation</button>
				</div>
			</form>
		</div>
	{:else}
		<div class="dock" class:selecting={picking}>
			{#if startError}
				<pre class="surface error" role="alert">{startError}</pre>
			{/if}
			<div class="surface tools">
				{#if ready}
					<button
						class="action"
						aria-pressed={picking}
						bind:this={launcher}
						disabled={!active}
						on:click={() => {
							picking = !picking;
							send(picking ? 'pick' : 'cancel');
							if (picking) frame?.focus();
						}}
					>
						{#if picking}<XMark />Cancel selection{:else}<ChatBubble />Annotate{/if}
					</button>
				{:else if preview.id === 'website' || preview.id === 'app'}
					<button class="action" disabled={starting || !active} on:click={startPreview}
						>{starting ? 'Starting…' : 'Start preview'}</button
					>
				{/if}
				{#if !picking}
					<details class="more">
						<summary aria-label="Preview options" title="Preview options"
							><EllipsisHorizontal /></summary
						>
						<div class="surface menu">
							<a
								href={preview.url}
								target="_blank"
								rel="noopener noreferrer"
								on:click={(e) => e.currentTarget.closest('details')?.removeAttribute('open')}
								>Open / sign in</a
							>
							<button
								on:click={(e) => {
									e.currentTarget.closest('details')?.removeAttribute('open');
									startError = '';
									frame.src = preview.url;
									connect();
								}}>Reload preview</button
							>
						</div>
					</details>
				{/if}
			</div>
		</div>
	{/if}
</div>

<style>
	.stage {
		--card-width: min(304px, calc(100% - 16px));
	}
	.surface {
		border: 1px solid var(--color-gray-200);
		background: white;
		color: var(--color-gray-900);
		box-shadow:
			0 2px 6px #0002,
			0 10px 28px #0002;
	}
	:global(.dark) .surface {
		background: var(--color-gray-900);
		color: var(--color-gray-100);
		border-color: var(--color-gray-700);
	}
	:global(.dark) .add {
		background: var(--color-gray-100);
		color: var(--color-gray-900);
	}
	.dock {
		position: absolute;
		right: 12px;
		bottom: 12px;
		max-width: calc(100% - 24px);
	}
	.dock.selecting {
		top: 12px;
		bottom: auto;
	}
	.tools {
		display: flex;
		width: fit-content;
		margin-left: auto;
		align-items: center;
		padding: 3px;
		border-radius: 99px;
	}
	.action,
	summary {
		display: flex;
		align-items: center;
		justify-content: center;
		height: 34px;
		border-radius: 99px;
		cursor: pointer;
	}
	.action {
		gap: 7px;
		padding: 0 11px;
		font-size: 13px;
		font-weight: 550;
	}
	.more {
		position: relative;
		border-left: 1px solid #8884;
	}
	summary {
		width: 34px;
		list-style: none;
	}
	summary::-webkit-details-marker {
		display: none;
	}
	.menu {
		position: absolute;
		right: -2px;
		bottom: calc(100% + 9px);
		width: max-content;
		min-width: 9rem;
		border-radius: 12px;
		padding: 4px;
		font-size: 13px;
	}
	.menu :is(a, button) {
		display: block;
		width: 100%;
		border-radius: 8px;
		text-align: left;
		padding: 8px 12px;
	}
	:is(.action, summary, .icon-button, .menu a, .menu button):hover {
		background: #8882;
	}
	.pin {
		position: absolute;
		width: 12px;
		height: 12px;
		border: 2px solid white;
		border-radius: 50%;
		transform: translate(-50%, -50%);
		background: #2563eb;
		box-shadow:
			0 0 0 1px #2563eb,
			0 1px 5px #0004;
	}
	.card {
		position: absolute;
		border-radius: 14px;
		padding: 9px 10px 10px;
		width: var(--card-width);
		max-height: calc(100% - 16px);
		overflow-y: auto;
	}
	.card.fallback {
		right: 8px;
		bottom: 8px;
	}
	.element-tag {
		border-radius: 5px;
		background: #8882;
		padding: 2px 5px;
		font-size: 11px;
	}
	.icon-button {
		display: grid;
		place-items: center;
		width: 28px;
		height: 28px;
		border-radius: 8px;
	}
	textarea {
		display: block;
		width: 100%;
		padding: 6px 2px;
		resize: none;
		background: transparent;
		font-size: 14px;
		line-height: 1.4;
	}
	.card:focus-within {
		border-color: var(--color-gray-400);
	}
	textarea:focus {
		outline: none;
	}
	.add {
		background: var(--color-gray-900);
		color: white;
		padding: 5px 10px;
		border-radius: 8px;
		font-size: 12px;
		font-weight: 550;
	}
	button:disabled {
		opacity: 0.5;
		cursor: default;
	}
	.error {
		padding: 10px;
		margin-bottom: 8px;
		border-radius: 10px;
		max-height: 7rem;
		overflow: auto;
		font-size: 12px;
		white-space: pre-wrap;
		overflow-wrap: anywhere;
	}
	@media (pointer: coarse) {
		.action,
		summary {
			min-width: 44px;
			min-height: 44px;
		}
		textarea {
			font-size: 16px;
		}
	}
</style>
