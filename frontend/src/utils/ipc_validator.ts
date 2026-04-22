type IpcEnvelope = {
	type: string;
	payload: Record<string, unknown>;
	timestamp?: string;
	request_id?: string;
};

const UUID_RE =
	/^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;

const allowedEnvelopeKeys = new Set(["type", "payload", "timestamp", "request_id"]);

function isIsoDate(value: string): boolean {
	const d = new Date(value);
	return !Number.isNaN(d.getTime());
}

export function validateIpcEnvelope(
	message: unknown,
): { valid: true; envelope: IpcEnvelope } | { valid: false; error: string } {
	if (typeof message !== "object" || message === null || Array.isArray(message)) {
		return { valid: false, error: "Message must be an object" };
	}

	const obj = message as Record<string, unknown>;

	const unknownKeys = Object.keys(obj).filter((key) => !allowedEnvelopeKeys.has(key));
	if (unknownKeys.length) {
		return { valid: false, error: `Unknown envelope keys: ${unknownKeys.join(", ")}` };
	}

	if (typeof obj.type !== "string" || !obj.type.trim()) {
		return { valid: false, error: "Field 'type' must be a non-empty string" };
	}

	if (
		typeof obj.payload !== "object" ||
		obj.payload === null ||
		Array.isArray(obj.payload)
	) {
		return { valid: false, error: "Field 'payload' must be an object" };
	}

	if (obj.timestamp !== undefined) {
		if (typeof obj.timestamp !== "string" || !isIsoDate(obj.timestamp)) {
			return { valid: false, error: "Field 'timestamp' must be ISO-8601" };
		}
	}

	if (obj.request_id !== undefined) {
		if (typeof obj.request_id !== "string" || !UUID_RE.test(obj.request_id)) {
			return { valid: false, error: "Field 'request_id' must be a UUID" };
		}
	}

	return {
		valid: true,
		envelope: {
			type: obj.type,
			payload: obj.payload as Record<string, unknown>,
			timestamp: obj.timestamp as string | undefined,
			request_id: obj.request_id as string | undefined,
		},
	};
}
