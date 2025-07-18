"""
Infinite Jukebox-style song remixing algorithm.

This module implements an algorithm that creates new versions of songs by
rearranging sections based on similarity analysis, similar to the original
Infinite Jukebox tool. It builds upon PyMusicLooper's existing similarity
detection to find sections that can be seamlessly connected.
"""

import logging
import random
from dataclasses import dataclass
from typing import Dict, List, Optional, Set, Tuple

import numpy as np
import librosa  # For converting frame counts to human-readable seconds

from .analysis import _analyze_audio, _calculate_subseq_beat_similarity, _weights
from .audio import MLAudio


@dataclass
class SectionNode:
    """Represents a section in the song that can be jumped to/from."""
    start_frame: int
    end_frame: int
    start_sample: int
    end_sample: int
    beat_index: int
    chroma_features: np.ndarray
    power_features: np.ndarray
    connections: List['SectionConnection']
    
    def __post_init__(self):
        if not hasattr(self, 'connections') or self.connections is None:
            self.connections = []


@dataclass
class SectionConnection:
    """Represents a connection between two similar sections."""
    target_node: SectionNode
    similarity_score: float
    note_distance: float
    loudness_difference: float
    
    def __repr__(self):
        return f"Connection(target_beat={self.target_node.beat_index}, score={self.similarity_score:.3f})"


class InfiniteJukebox:
    """
    Creates remixed versions of songs by finding similar sections and jumping between them.
    
    This algorithm analyzes a song to find sections that sound similar enough to be
    seamlessly connected, then generates new arrangements by randomly or deterministically
    jumping between these similar sections.
    """
    
    def __init__(self, 
                 similarity_threshold: float = 0.7,
                 max_connections_per_section: int = 10,
                 min_section_duration: float = 2.0,
                 max_section_duration: float = 8.0,
                 num_section_clusters: int = 4):
        """
        Initialize the Infinite Jukebox remixer.
        
        Args:
            similarity_threshold: Minimum similarity score for connections (0.0-1.0)
            max_connections_per_section: Maximum number of connections per section
            min_section_duration: Minimum duration in seconds for a section
            max_section_duration: Maximum duration in seconds for a section
        """
        self.similarity_threshold = similarity_threshold
        self.max_connections_per_section = max_connections_per_section
        self.min_section_duration = min_section_duration
        self.max_section_duration = max_section_duration
        self.num_section_clusters = num_section_clusters
        self.section_labels: Optional[np.ndarray] = None  # cluster label per node
        self.nodes: List[SectionNode] = []
        self.connection_map: Dict[int, List[SectionConnection]] = {}
        
    def analyze_song(self, mlaudio: MLAudio) -> None:
        """
        Analyze the song to find similar sections and build the connection graph.
        
        Args:
            mlaudio: The audio file to analyze
        """
        logging.info("Starting Infinite Jukebox analysis...")
        print("DEBUG: In analyze_song method")
        
        # Get audio features using existing PyMusicLooper analysis
        print("DEBUG: About to call _analyze_audio")
        chroma, power_db, bpm, beats = _analyze_audio(mlaudio)
        print(f"DEBUG: _analyze_audio returned - chroma shape: {chroma.shape}, power_db shape: {power_db.shape}, bpm: {bpm}, beats length: {len(beats)}")
        
        # Convert bpm to scalar if it's an array
        if hasattr(bpm, 'item'):
            bpm = bpm.item()
        elif isinstance(bpm, (list, tuple, np.ndarray)):
            bpm = float(bpm[0]) if len(bpm) > 0 else 120.0
        else:
            bpm = float(bpm)
        
        print(f"DEBUG: bpm converted to scalar: {bpm}, type: {type(bpm)}")
        
        # Store for potential retry
        self.chroma = chroma
        self.bpm = bpm
        
        # Create section nodes from beats
        self._create_section_nodes(mlaudio, chroma, power_db, beats, bpm)
        
        # Find connections between similar sections
        self._find_section_connections(mlaudio, chroma, bpm)

        # --- High-level clustering for compositional generation ---
        self._cluster_sections()
        
        logging.info(f"Created {len(self.nodes)} sections with {sum(len(node.connections) for node in self.nodes)} total connections")
    
    def _create_section_nodes(self, 
                             mlaudio: MLAudio,
                             chroma: np.ndarray,
                             power_db: np.ndarray,
                             beats: np.ndarray,
                             bpm: float) -> None:
        """Create section nodes from detected beats."""
        min_frames = mlaudio.seconds_to_frames(self.min_section_duration)
        max_frames = mlaudio.seconds_to_frames(self.max_section_duration)
        
        self.nodes = []
        
        print(f"DEBUG: Creating sections - bpm type: {type(bpm)}, value: {bpm}")
        logging.info(f"Creating sections from {len(beats)} beats, BPM: {bpm:.1f}")
        
        # Show min/max frames also in seconds for clarity
        min_sec = librosa.frames_to_time(min_frames, sr=mlaudio.rate)
        max_sec = librosa.frames_to_time(max_frames, sr=mlaudio.rate)
        print(
            f"DEBUG: min_frames: {min_frames} ({min_sec:.3f}s), "
            f"max_frames: {max_frames} ({max_sec:.3f}s)"
        )
        print(
            f"DEBUG: min_section_duration (requested): {self.min_section_duration}s, "
            f"max_section_duration (requested): {self.max_section_duration}s"
        )
        
        for i, beat_frame in enumerate(beats):
            # Calculate section duration based on tempo
            beats_per_section = max(4, int(bpm / 60 * self.min_section_duration))
            
            # Find the end of this section
            if i + beats_per_section < len(beats):
                end_frame = beats[i + beats_per_section]
            else:
                end_frame = min(beat_frame + max_frames, chroma.shape[-1] - 1)
            
            # Duration metrics
            duration_frames = end_frame - beat_frame
            duration_sec = librosa.frames_to_time(duration_frames, sr=mlaudio.rate)
            print(
                "DEBUG: Beat {idx}: beat_frame={b_frame}, end_frame={e_frame}, "
                "duration={dur_f} frames ({dur_s:.3f}s), min_duration={min_f} "
                "frames ({min_s:.3f}s)".format(
                    idx=i,
                    b_frame=beat_frame,
                    e_frame=end_frame,
                    dur_f=duration_frames,
                    dur_s=duration_sec,
                    min_f=min_frames,
                    min_s=min_sec,
                )
            )
            
            # Ensure minimum duration
            if end_frame - beat_frame < min_frames:
                print(
                    "DEBUG: Skipping beat {idx} - duration too short: {dur_s:.3f}s "
                    "< {min_s:.3f}s".format(idx=i, dur_s=duration_sec, min_s=min_sec)
                )
                continue
                
            # Create the section node
            print(f"DEBUG: Creating section node for beat {i}")
            node = SectionNode(
                start_frame=int(beat_frame),
                end_frame=int(end_frame),
                start_sample=mlaudio.frames_to_samples(beat_frame),
                end_sample=mlaudio.frames_to_samples(end_frame),
                beat_index=i,
                chroma_features=chroma[:, beat_frame:end_frame],
                power_features=power_db[:, beat_frame:end_frame],
                connections=[]
            )
            self.nodes.append(node)
            print(f"DEBUG: Section node created and added. Total nodes: {len(self.nodes)}")
            
        logging.info(f"Created {len(self.nodes)} sections")
    
    def _find_section_connections(self, mlaudio: MLAudio, chroma: np.ndarray, bpm: float) -> None:
        """Find connections between similar sections.

        This implementation performs a two-stage matching process to vastly reduce
        the number of expensive similarity calculations:

        1.  A fast pre-filter based on the cosine similarity of **average** chroma
            vectors for each section is computed for *all* pairs in one matrix
            multiplication.  Only pairs above `similarity_threshold` (and at most
            `prefilter_k` per section) are kept for the next step.
        2.  The original, higher-fidelity similarity metric
            (`_calculate_section_similarity`) is then evaluated **only** for this
            much smaller candidate set.
        """

        n_nodes = len(self.nodes)
        if n_nodes == 0:
            return

        # ---- 1.  Fast pre-filter using average chroma cosine similarity ----
        # Pre-compute average chroma (12-dim) for every section
        avg_chroma = np.stack([
            np.mean(node.chroma_features, axis=1, dtype=np.float32) for node in self.nodes
        ])  # shape: (N, 12)

        # L2-normalise so that dot-product equals cosine similarity
        norms = np.linalg.norm(avg_chroma, axis=1, keepdims=True)
        norms[norms == 0] = 1.0  # protect against division by zero
        norm_chroma = avg_chroma / norms

        # Cosine similarity matrix – uses efficient BLAS GEMM under the hood
        sim_matrix = norm_chroma @ norm_chroma.T  # shape: (N, N)
        # Ignore self-similarity
        np.fill_diagonal(sim_matrix, 0.0)

        # Pre-compute quick loudness metric for each node (max power over section)
        loudness_arr = np.array([
            float(np.mean(np.max(node.power_features, axis=0))) for node in self.nodes
        ], dtype=np.float32)

        # We'll only run the expensive similarity calc on the *k* most similar
        # sections (above threshold) for each node.
        prefilter_k = self.max_connections_per_section * 5

        # Calculate test-duration and weights once for the detailed metric.
        beats_per_second = bpm / 60.0
        num_test_beats = 8
        seconds_to_test = num_test_beats / beats_per_second
        # Frames per second in the chroma representation: librosa defaults
        # hop_length=512.
        frames_per_second = mlaudio.rate / 512  # ≈ 86 for 44.1 kHz
        test_duration = int(seconds_to_test * frames_per_second)
        weights = _weights(min(test_duration, 20), start=10, stop=1)

        logging.info(
            "Finding connections with fast pre-filter: nodes=%d, k=%d, threshold=%.2f",
            n_nodes, prefilter_k, self.similarity_threshold,
        )

        for i, node_a in enumerate(self.nodes):
            # Get indices of potential matches sorted by fast cosine similarity
            sim_row = sim_matrix[i]
            # Keep only indices above the fast threshold
            candidate_idx = np.flatnonzero(sim_row >= self.similarity_threshold)
            if candidate_idx.size == 0:
                self.connection_map[i] = []
                continue

            # Sort candidates by descending similarity and keep top-k
            sorted_idx = candidate_idx[np.argsort(sim_row[candidate_idx])[::-1]]
            sorted_idx = sorted_idx[:prefilter_k]

            connections: List[SectionConnection] = []

            for j in sorted_idx:
                node_b = self.nodes[j]
                # Detailed similarity – still relatively costly but run on far
                # fewer pairs now.
                detailed_sim = self._calculate_section_similarity(
                    node_a,
                    node_b,
                    chroma,
                    test_duration,
                    weights,
                )

                if detailed_sim < self.similarity_threshold:
                    continue  # ignore low-quality match after refinement

                # Compute additional metrics
                note_distance = np.linalg.norm(avg_chroma[i] - avg_chroma[j])
                loudness_difference = abs(loudness_arr[i] - loudness_arr[j])

                connections.append(
                    SectionConnection(
                        target_node=node_b,
                        similarity_score=float(detailed_sim),
                        note_distance=float(note_distance),
                        loudness_difference=float(loudness_difference),
                    )
                )

            # Keep the best connections per section
            connections.sort(key=lambda c: c.similarity_score, reverse=True)
            node_a.connections = connections[: self.max_connections_per_section]
            self.connection_map[i] = node_a.connections

        # Optionally, collect some statistics for logging
        num_conn = sum(len(n.connections) for n in self.nodes)
        logging.info("Generated %d connections across %d sections", num_conn, n_nodes)
    
    def _calculate_section_similarity(self, 
                                    node_a: SectionNode,
                                    node_b: SectionNode,
                                    chroma: np.ndarray,
                                    test_duration: int,
                                    weights: np.ndarray) -> float:
        """Calculate similarity between two sections using existing similarity algorithm."""
        # Use the existing similarity calculation from PyMusicLooper
        print(f"DEBUG: _calculate_section_similarity called with node_a.start_frame: {node_a.start_frame}, node_b.start_frame: {node_b.start_frame}")
        
        result = _calculate_subseq_beat_similarity(
            node_a.start_frame,
            node_b.start_frame,
            chroma,
            min(test_duration, node_a.end_frame - node_a.start_frame),
            weights=weights
        )
        
        print(f"DEBUG: _calculate_subseq_beat_similarity returned type: {type(result)}, value: {result}")
        return result
    
    def _calculate_note_distance(self, node_a: SectionNode, node_b: SectionNode) -> float:
        """Calculate harmonic distance between two sections."""
        # Average chroma features over the section
        chroma_a = np.mean(node_a.chroma_features, axis=1)
        chroma_b = np.mean(node_b.chroma_features, axis=1)
        
        # Calculate Euclidean distance
        return np.sqrt(np.sum((chroma_a - chroma_b) ** 2))
    
    def _calculate_loudness_difference(self, node_a: SectionNode, node_b: SectionNode) -> float:
        """Calculate loudness difference between two sections."""
        # Average power over the section
        power_a = np.mean(np.max(node_a.power_features, axis=0))
        power_b = np.mean(np.max(node_b.power_features, axis=0))
        
        return abs(power_a - power_b)

    # ------------------------------------------------------------------
    # Section clustering & composition generation
    # ------------------------------------------------------------------

    def _cluster_sections(self) -> None:
        """Cluster sections into *num_section_clusters* groups based on average chroma.

        A simple k-means implementation is used to avoid the heavyweight scikit-learn
        dependency.  The resulting labels are stored in *self.section_labels* and
        also attached to each *SectionNode* via a dynamic *cluster_label* attribute.
        """

        if not self.nodes:
            self.section_labels = None
            return

        k = max(1, int(self.num_section_clusters))
        if k == 1:
            self.section_labels = np.zeros(len(self.nodes), dtype=int)
            for node in self.nodes:
                setattr(node, "cluster_label", 0)
            return

        # --- Prepare feature matrix: average chroma per section (12-D) ---
        data = np.stack([np.mean(node.chroma_features, axis=1, dtype=np.float32) for node in self.nodes])

        # --- Tiny k-means (Euclidean) ---
        rng = np.random.default_rng(0)
        centroids = data[rng.choice(len(data), size=k, replace=False)]  # (k, 12)

        for _ in range(100):  # max iterations
            # Assign step
            dist = np.linalg.norm(data[:, None, :] - centroids[None, :, :], axis=2)  # (N, k)
            labels = np.argmin(dist, axis=1)  # (N,)

            # Update step
            new_centroids = np.array([
                data[labels == i].mean(axis=0) if np.any(labels == i) else centroids[i]
                for i in range(k)
            ])

            if np.allclose(new_centroids, centroids):
                break
            centroids = new_centroids

        self.section_labels = labels.astype(int)

        # Attach label to each node for downstream use
        for node, lbl in zip(self.nodes, self.section_labels):
            setattr(node, "cluster_label", int(lbl))

    # ---------------------------------------------------------------
    # Public API: structured composition similar to hip-hop song form
    # ---------------------------------------------------------------

    def generate_composition(
        self,
        mlaudio: MLAudio,
        section_order: List[int],
        loops_per_section: int = 4,
        prefer_similar: bool = True,
        seed: Optional[int] = None,
    ) -> List[SectionNode]:
        """Generate a structured composition following *section_order*.

        Parameters
        ----------
        mlaudio
            The MLAudio instance for timing information.
        section_order
            List of cluster indices representing the desired macro-structure
            (e.g., ``[0, 1, 2, 1, 2]`` for intro-verse-chorus-verse-chorus).
            Valid indices are ``0 … num_section_clusters-1``.
        loops_per_section
            How many loops (SectionNode instances) to pick for each macro section.
        prefer_similar
            Whether to bias transitions within a macro section towards more
            similar neighbours (uses connection graph weights).
        seed
            Optional RNG seed for reproducibility.
        """

        if seed is not None:
            random.seed(seed)

        if not self.nodes or self.section_labels is None:
            raise ValueError("No analysis/clustering available. Call analyze_song() first.")

        # Build mapping from cluster label to nodes list
        clusters: Dict[int, List[SectionNode]] = {}
        for node, lbl in zip(self.nodes, self.section_labels):
            clusters.setdefault(int(lbl), []).append(node)

        composition: List[SectionNode] = []

        for lbl in section_order:
            if lbl not in clusters or not clusters[lbl]:
                continue  # skip unknown label

            # Start with a random node from this cluster
            current = random.choice(clusters[lbl])

            for _ in range(loops_per_section):
                composition.append(current)

                # Transition within same cluster
                same_cluster_conns = [c for c in current.connections if getattr(c.target_node, "cluster_label", -1) == lbl]

                if prefer_similar and same_cluster_conns:
                    # Weighted by similarity
                    weights = [c.similarity_score for c in same_cluster_conns]
                    total_w = sum(weights)
                    if total_w > 0:
                        weights = [w / total_w for w in weights]
                        current = random.choices([c.target_node for c in same_cluster_conns], weights=weights)[0]
                        continue

                # Fallback: random node in cluster
                current = random.choice(clusters[lbl])

        return composition

    # ---------------------------------------------------------------
    # Convenience helpers
    # ---------------------------------------------------------------

    def suggest_section_order(self) -> List[int]:
        """Return a basic intro→verse→chorus style order based on cluster sizes.

        Clusters are sorted by average loudness (softest assumed intro, loudest chorus).
        The resulting order is `[intro, verse, chorus, verse, chorus]` if we have
        at least 3 clusters, otherwise it falls back to sequential labels.
        """
        if self.section_labels is None:
            raise ValueError("Requires analyze_song() to be called.")

        # Compute loudness per cluster
        cluster_loudness: Dict[int, float] = {}
        for lbl in np.unique(self.section_labels):
            secs = [n for n in self.nodes if getattr(n, "cluster_label", -1) == lbl]
            loud = np.mean([
                np.mean(np.max(n.power_features, axis=0)) for n in secs
            ]) if secs else 0.0
            cluster_loudness[lbl] = loud

        # Sort clusters: soft→loud
        sorted_lbl = sorted(cluster_loudness, key=lambda l: cluster_loudness[l])

        if len(sorted_lbl) >= 3:
            intro, verse, chorus = sorted_lbl[:3]
            return [intro, verse, chorus, verse, chorus]
        else:
            return sorted_lbl

    def export_composition_audio(
        self,
        mlaudio: MLAudio,
        composition_sections: List[SectionNode],
        output_path: str,
        fade_duration: float = 0.1,
    ) -> None:
        """Wrapper around *export_remix_audio* for clarity."""
        self.export_remix_audio(
            mlaudio,
            composition_sections,
            output_path,
            fade_duration=fade_duration,
        )
    
    def generate_remix(self, 
                      mlaudio: MLAudio,
                      target_duration: float,
                      jump_probability: float = 0.3,
                      prefer_similar: bool = True,
                      seed: Optional[int] = None) -> List[SectionNode]:
        """
        Generate a remixed version of the song.
        
        Args:
            target_duration: Desired duration of the remix in seconds
            jump_probability: Probability of jumping to a similar section vs. continuing
            prefer_similar: Whether to prefer more similar sections when jumping
            seed: Random seed for reproducible results
            
        Returns:
            List of section nodes representing the remixed song structure
        """
        if seed is not None:
            random.seed(seed)
        
        if not self.nodes:
            raise ValueError("No sections analyzed. Call analyze_song() first.")
        
        remix_sections = []
        current_node = random.choice(self.nodes)  # Start with a random section
        total_duration = 0
        
        while total_duration < target_duration:
            # Add current section to remix
            remix_sections.append(current_node)
            section_duration = (current_node.end_sample - current_node.start_sample) / mlaudio.rate  # Convert samples to seconds
            total_duration += section_duration
            
            # Decide whether to jump or continue
            if random.random() < jump_probability and current_node.connections:
                # Jump to a similar section
                if prefer_similar:
                    # Weight selection by similarity score
                    weights = [conn.similarity_score for conn in current_node.connections]
                    total_weight = sum(weights)
                    if total_weight > 0:
                        weights = [w / total_weight for w in weights]
                        current_node = random.choices(
                            [conn.target_node for conn in current_node.connections],
                            weights=weights
                        )[0]
                    else:
                        current_node = random.choice(current_node.connections).target_node
                else:
                    # Random selection from connections
                    current_node = random.choice(current_node.connections).target_node
            else:
                # Continue to next section in sequence
                current_index = next(i for i, node in enumerate(self.nodes) if node == current_node)
                if current_index + 1 < len(self.nodes):
                    current_node = self.nodes[current_index + 1]
                else:
                    # Wrap around or jump to a random section
                    if self.nodes[0].connections:
                        current_node = random.choice(self.nodes[0].connections).target_node
                    else:
                        current_node = random.choice(self.nodes)
        
        return remix_sections
    
    def get_connection_stats(self) -> Dict[str, float]:
        """Get statistics about the section connections."""
        if not self.nodes:
            return {}
        
        total_connections = sum(len(node.connections) for node in self.nodes)
        avg_connections = total_connections / len(self.nodes)
        
        all_scores = []
        for node in self.nodes:
            all_scores.extend([conn.similarity_score for conn in node.connections])
        
        print(f"DEBUG: get_connection_stats - all_scores type: {type(all_scores)}")
        print(f"DEBUG: get_connection_stats - all_scores sample: {all_scores[:5] if len(all_scores) > 5 else all_scores}")
        
        if all_scores:
            avg_score = float(np.mean(all_scores))
            max_score = float(np.max(all_scores))
            min_score = float(np.min(all_scores))
            
            print(f"DEBUG: avg_score type: {type(avg_score)}, value: {avg_score}")
            print(f"DEBUG: max_score type: {type(max_score)}, value: {max_score}")
            print(f"DEBUG: min_score type: {type(min_score)}, value: {min_score}")
        else:
            avg_score = max_score = min_score = 0
        
        return {
            'total_sections': len(self.nodes),
            'total_connections': total_connections,
            'avg_connections_per_section': avg_connections,
            'avg_similarity_score': avg_score,
            'max_similarity_score': max_score,
            'min_similarity_score': min_score,
        }
    
    def export_remix_audio(self, 
                          mlaudio: MLAudio, 
                          remix_sections: List[SectionNode],
                          output_path: str,
                          fade_duration: float = 0.1) -> None:
        """
        Export the remixed audio to a file.
        
        Args:
            mlaudio: The original audio file
            remix_sections: List of sections from generate_remix()
            output_path: Path to save the remixed audio
            fade_duration: Duration of crossfade between sections in seconds
        """
        import soundfile as sf
        
        # Build the remixed audio
        remix_audio = []
        fade_samples = int(fade_duration * mlaudio.rate)
        
        for i, section in enumerate(remix_sections):
            # Extract section audio
            section_audio = mlaudio.playback_audio[section.start_sample:section.end_sample]
            
            # Apply crossfade if not the first section
            if i > 0 and fade_samples > 0:
                # Fade out previous section
                if len(remix_audio) > fade_samples:
                    fade_out = np.linspace(1, 0, fade_samples)
                    if mlaudio.playback_audio.ndim == 2:
                        fade_out = fade_out[:, np.newaxis]
                    remix_audio[-fade_samples:] *= fade_out
                
                # Fade in current section
                if len(section_audio) > fade_samples:
                    fade_in = np.linspace(0, 1, fade_samples)
                    if section_audio.ndim == 2:
                        fade_in = fade_in[:, np.newaxis]
                    section_audio[:fade_samples] *= fade_in
            
            remix_audio.extend(section_audio)
        
        # Convert to numpy array and save
        remix_audio = np.array(remix_audio)
        sf.write(output_path, remix_audio, mlaudio.rate)
        logging.info(f"Remixed audio saved to: {output_path}")