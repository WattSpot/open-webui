import { describe, expect, it } from 'vitest';
import {
	agentDirectory,
	annotationPrompt,
	readAnnotationPrompt,
	matchesPreviewRoot,
	previewSelection,
	restoreAnnotations
} from './previewAnnotations';

const selection = {
	root: '/repo/task',
	url: 'https://preview.example/path',
	selector: 'button:nth-child(1)',
	tag: 'button',
	role: '',
	label: 'Continue',
	text: 'Continue'
};
const annotation = { ...selection, id: 'note', terminalId: 'owner', comment: 'Make this clearer' };

describe('preview draft boundary', () => {
	it('accepts a folder picker trailing slash only for the same checkout', () => {
		expect(matchesPreviewRoot('/repo/task', '/repo/task/')).toBe(true);
		expect(matchesPreviewRoot('/repo/task', '/repo/task-2/')).toBe(false);
		expect(matchesPreviewRoot('/repo/task', undefined)).toBe(false);
	});
	it('accepts bounded context only from the configured preview origin', () => {
		expect(previewSelection(selection, 'https://preview.example')).toEqual(selection);
		for (const value of [
			null,
			{},
			{ ...selection, root: 'relative' },
			{ ...selection, text: 'x'.repeat(301) },
			{ ...selection, url: `${selection.url}?token=secret` },
			{ ...selection, url: `${selection.url}#secret` },
			{ ...selection, url: 'https://other.example/path' }
		]) {
			expect(previewSelection(value, 'https://preview.example')).toBeNull();
		}
	});
	it('restores comments and serializes them once as ordinary prompt text', () => {
		expect(restoreAnnotations([annotation, { ...annotation, comment: '' }])).toEqual([annotation]);
		expect(restoreAnnotations(Array(21).fill(annotation))).toEqual([]);
		const prompt = annotationPrompt('Please fix', [annotation]);
		expect(prompt).toContain('Please fix');
		expect(prompt.match(/Make this clearer/g)).toHaveLength(1);
		expect(prompt).not.toContain('terminalId');
		expect(annotationPrompt('unchanged', [])).toBe('unchanged');
	});
	it('renders sent notes separately while preserving ordinary or malformed messages', () => {
		const second = {
			...annotation,
			source: 'src/Continue.tsx:12',
			component: 'Continue',
			comment: 'Second line\nExtra context'
		};
		for (const prompt of ['', 'Please **review**']) {
			const encoded = annotationPrompt(prompt, [annotation, second]);
			const display = readAnnotationPrompt(encoded);
			expect(display?.prompt).toBe(prompt);
			expect(display?.notes.map((n) => n.comment)).toEqual([annotation.comment, second.comment]);
			expect(display?.notes[1].source).toBe(second.source);
			expect(display?.notes[1].component).toBe(second.component);
			expect(display?.notes[0].selector).toBe(selection.selector);
			expect(readAnnotationPrompt(encoded + '\nordinary text')).toBeNull();
		}
		expect(readAnnotationPrompt('Ordinary chat')).toBeNull();
	});
	it('uses the agent conversation directory instead of the file browser directory', () => {
		const history = {
			currentId: 'user',
			messages: {
				user: { parentId: 'assistant' },
				assistant: { meta: { agent_cwd: '/repo/task' } }
			}
		};
		expect(agentDirectory(history)).toBe('/repo/task');
		expect(agentDirectory({ currentId: null, messages: {} })).toBeNull();
	});
});
