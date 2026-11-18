<script lang="ts">
	import { onDestroy } from 'svelte';
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
		if (data.action === 'ready') ready = true;
		if (!active) return;
		if (data.action === 'cancel') picking = false;
		if (data.action === 'selection' && picking) {
			selection = previewSelection(data.selection, origin);
			picking = false;
		}
	};
</script>

<svelte:window on:message={receive} />
<div class="flex h-full min-h-0 flex-col bg-white dark:bg-gray-900">
	<div
		class="flex flex-wrap items-center gap-3 border-b border-gray-100 p-2 text-xs dark:border-gray-800"
	>
		{#if !ready && (preview.id === 'website' || preview.id === 'app')}
			<button
				class="rounded-lg bg-gray-900 px-3 py-2 text-white disabled:opacity-40 dark:bg-gray-100 dark:text-gray-900"
				disabled={starting || !active}
				on:click={startPreview}>{starting ? 'Starting…' : 'Start preview'}</button
			>
		{/if}
		<button
			class="rounded-lg bg-gray-100 px-3 py-2 disabled:opacity-40 dark:bg-gray-800"
			disabled={!ready || !active}
			on:click={() => {
				picking = !picking;
				send(picking ? 'pick' : 'cancel');
			}}>{picking ? 'Cancel selection' : 'Comment on element'}</button
		>
		<a class="underline" href={preview.url} target="_blank" rel="noopener noreferrer"
			>Open / sign in</a
		>
		<button
			class="underline"
			on:click={() => {
				frame.src = preview.url;
				connect();
			}}>Reload</button
		>
		{#if !ready}<span role="status"
				>If Coder asks you to sign in, open the preview above, then reload.</span
			>{/if}
	</div>
	{#if startError}
		<pre
			role="alert"
			class="max-h-40 overflow-auto whitespace-pre-wrap border-b p-2 text-xs">{startError}</pre>
	{/if}
	{#if selection}
		<form
			class="space-y-2 border-b p-3 text-sm dark:border-gray-800"
			on:submit|preventDefault={() => {
				if (selection && comment.trim() && onAnnotate(selection, comment.trim())) {
					selection = null;
					comment = '';
				}
			}}
		>
			<p class="truncate font-medium">{selection.label || selection.text || selection.selector}</p>
			<label class="block"
				>Comment<textarea
					class="mt-1 w-full rounded-lg border bg-transparent p-2 dark:border-gray-700"
					bind:value={comment}
					maxlength="2000"
					required
					rows="2"
				></textarea></label
			>
			<div class="flex items-center gap-3">
				<button
					class="rounded-lg bg-gray-900 px-3 py-2 text-white dark:bg-gray-100 dark:text-gray-900"
					disabled={!comment.trim()}>Add to draft</button
				><button
					type="button"
					class="underline"
					on:click={() => {
						selection = null;
						comment = '';
					}}>Cancel</button
				><span class="text-xs text-gray-500">Sent only when you send the chat message.</span>
			</div>
		</form>
	{/if}
	<iframe
		bind:this={frame}
		src={preview.url}
		title={`${preview.label} preview`}
		class="min-h-0 w-full flex-1 border-0"
		on:load={connect}
		sandbox="allow-scripts allow-same-origin allow-forms allow-popups allow-popups-to-escape-sandbox allow-downloads"
	></iframe>
</div>
