<script lang="ts">
	import {
		previewSelection,
		type Preview,
		type PreviewSelection
	} from '$lib/utils/previewAnnotations';
	export let preview: Preview;
	export let active: boolean;
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
				>Start this preview in your Workbot. Sign in above, then reload.</span
			>{/if}
	</div>
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
