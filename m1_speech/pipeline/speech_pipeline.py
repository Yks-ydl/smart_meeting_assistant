from __future__ import annotations

from pathlib import Path

from m1_speech.asr.transcriber import ASRTranscriber
from m1_speech.asr.vad import VADProcessor
from m1_speech.io.audio_input_manager import AudioInputManager
from m1_speech.io.transcript_exporter import TranscriptExporter
from m1_speech.pipeline.attribution import ChannelSpeakerAttributor
from m1_speech.pipeline.merger import TranscriptMerger
from m1_speech.postprocess.text_postprocessor import TextPostProcessor
from m1_speech.utils.config import ConfigLoader, PipelineConfig
from m1_speech.utils.schemas import TranscriptSegment


class SpeechPipeline:
    """M1 语音模块端到端流水线。"""

    def __init__(
        self,
        audio_input_manager: AudioInputManager,
        vad_processor: VADProcessor,
        transcriber: ASRTranscriber,
        speaker_attributor: ChannelSpeakerAttributor,
        transcript_merger: TranscriptMerger,
        text_postprocessor: TextPostProcessor,
    ) -> None:
        self.audio_input_manager = audio_input_manager
        self.vad_processor = vad_processor
        self.transcriber = transcriber
        self.speaker_attributor = speaker_attributor
        self.transcript_merger = transcript_merger
        self.text_postprocessor = text_postprocessor

    @classmethod
    def from_config(cls, config: PipelineConfig) -> "SpeechPipeline":
        """从配置对象构建完整流水线。"""

        return cls(
            audio_input_manager=AudioInputManager(
                config=config.input,
                target_sample_rate=config.asr.sample_rate,
            ),
            vad_processor=VADProcessor(config=config.vad),
            transcriber=ASRTranscriber(config=config.asr),
            speaker_attributor=ChannelSpeakerAttributor(config=config.speaker),
            transcript_merger=TranscriptMerger(),
            text_postprocessor=TextPostProcessor(config=config.postprocess),
        )

    @classmethod
    def from_config_path(cls, config_path: str | Path) -> tuple["SpeechPipeline", PipelineConfig]:
        """从 JSON 配置文件构建流水线。"""

        config = ConfigLoader.load(config_path)
        return cls.from_config(config), config

    def run(self, input_dir: str | Path) -> list[TranscriptSegment]:
        """执行多音轨会议转写流程。"""

        sources = self.audio_input_manager.discover_audio_sources(input_dir)
        speaker_labels = self.speaker_attributor.assign_labels(sources)

        transcript_groups: list[list[TranscriptSegment]] = []
        for source in sources:
            waveform, sample_rate = self.audio_input_manager.load_waveform(source)
            processed_waveform, offset_seconds = self.vad_processor.preprocess(waveform, sample_rate)

            speaker_label = speaker_labels[source.source_id]
            segments = self.transcriber.transcribe(
                waveform=processed_waveform,
                sample_rate=sample_rate,
                source_channel=source.source_id,
                speaker_label=speaker_label,
                start_offset=offset_seconds,
            )
            transcript_groups.append(segments)

        merged_segments = self.transcript_merger.merge(transcript_groups)
        return self.text_postprocessor.process_segments(merged_segments)

    def run_and_export(
        self,
        input_dir: str | Path,
        output_dir: str | Path,
        json_name: str = "merged_transcript.json",
        txt_name: str = "merged_transcript.txt",
    ) -> tuple[list[TranscriptSegment], Path, Path]:
        """执行流水线并导出 JSON / TXT。"""

        output_path = Path(output_dir)
        segments = self.run(input_dir)
        json_path = TranscriptExporter.export_json(segments, output_path / json_name)
        txt_path = TranscriptExporter.export_txt(segments, output_path / txt_name)
        return segments, json_path, txt_path
