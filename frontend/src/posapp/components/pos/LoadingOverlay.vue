<template>
	<v-overlay
		:model-value="loading"
		class="d-flex flex-column align-center justify-center fancy-overlay"
		contained
	>
		<v-progress-linear
			:model-value="progress"
			height="8"
			color="primary"
			rounded
			class="elegant-progress"
		/>
		<div class="mt-4 text-subtitle-1">{{ message }}</div>
	</v-overlay>
</template>

<script>
export default {
	name: "LoadingOverlay",
	props: {
		loading: {
			type: Boolean,
			default: false,
		},
		message: {
			type: String,
			default: "",
		},
		progress: {
			type: Number,
			default: 0,
		},
	},
};
</script>

<style scoped>
.fancy-overlay {
	backdrop-filter: blur(2px);
}
.elegant-progress {
	width: 60%;
	max-width: 320px;
}
</style>
