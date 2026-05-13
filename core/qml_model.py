"""
QML Placement Model using PennyLane VQC
Sky130-tuned Quantum Machine Learning circuit for cell placement optimization
"""

import torch
import torch.nn as nn
import numpy as np
import pennylane as qml
from pennylane import numpy as pnp
from typing import Tuple, Optional


class QuantumPlacementCircuit(nn.Module):
    """Variational Quantum Circuit for placement coordinate generation."""
    
    def __init__(self, n_qubits: int = 8, n_layers: int = 4, 
                 diff_method: str = "adjoint", device_name: str = "default.qubit"):
        """
        Args:
            n_qubits: Number of qubits in VQC
            n_layers: Number of VQC layers
            diff_method: Differentiation method ('parameter-shift' or 'adjoint')
            device_name: PennyLane device ('lightning.gpu' if available, else 'default.qubit')
        
        Note:
            - Quantum circuit runs on CPU (initialization only, small overhead)
            - PyTorch gradient descent runs on GPU (handles heavy optimization)
            - This hybrid approach is optimal for placement optimization
        """
        super().__init__()
        self.n_qubits = n_qubits
        self.n_layers = n_layers
        self.diff_method = diff_method
        self.circuit_cache = None
        
        # Detect GPU availability with proper error handling
        try:
            import logging
            logger = logging.getLogger(__name__)
            dev = qml.device("lightning.gpu", wires=n_qubits)
            self.device_name = "lightning.gpu"
            logger.info(f"[QML_MODEL] Quantum circuit: PennyLane lightning.gpu ({n_qubits} qubits, {n_layers} layers)")
        except ImportError as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.info(f"[QML_MODEL] Quantum circuit: PennyLane CPU (lightning.gpu not available: {e})")
            dev = qml.device(device_name, wires=n_qubits)
            self.device_name = device_name
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.info(f"[QML_MODEL] Quantum circuit: PennyLane CPU (initialization only, PyTorch handles GPU optimization)")
            dev = qml.device(device_name, wires=n_qubits)
            self.device_name = device_name
        
        self.dev = dev
        
        # VQC parameters: RY and RZ rotations per qubit per layer
        # Shape: [n_layers, n_qubits, 2] (2 for RY and RZ)
        self.params = nn.Parameter(
            torch.randn(n_layers, n_qubits, 2) * 0.1
        )
        
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
        Run VQC on input batch (vectorized).
        
        Args:
            x: Input features [batch_size, 8] (normalized cell features)
            
        Returns:
            Placement coordinates [batch_size, 2] normalized to [0, 1]
        """
        batch_size = x.shape[0]
        output = np.zeros((batch_size, 2))
        
        params_np = self.params.detach().cpu().numpy()
        x_np = x.detach().cpu().numpy()
        
        # Cache circuit on first use
        if self.circuit_cache is None:
            self.circuit_cache = self._build_circuit()
        
        # Process each sample in batch
        for i in range(batch_size):
            circuit_input = x_np[i]
            result = self.circuit_cache(circuit_input, params_np)
            # Map measurement results to [0, 1] coordinates
            output[i, 0] = (float(result[0]) + 1.0) / 2.0  # Map [-1, 1] to [0, 1]
            output[i, 1] = (float(result[1]) + 1.0) / 2.0
        
        return torch.FloatTensor(output)
    
    def _build_circuit(self):
        """Build and cache the quantum circuit (called once)."""
        @qml.qnode(self.dev, diff_method=self.diff_method)
        def circuit(features, params_flat):
            # Encode input features into qubit rotations
            for q in range(self.n_qubits):
                if q < len(features):
                    angle = np.pi * features[q]
                    qml.RY(angle, wires=q)
            
            # Parameterized VQC layers
            params_reshaped = params_flat.reshape(self.n_layers, self.n_qubits, 2)
            for layer in range(self.n_layers):
                # RY-RZ layer on each qubit
                for q in range(self.n_qubits):
                    qml.RY(params_reshaped[layer, q, 0], wires=q)
                    qml.RZ(params_reshaped[layer, q, 1], wires=q)
                
                # Entangling layer: CNOT chain
                for q in range(self.n_qubits - 1):
                    qml.CNOT(wires=[q, q + 1])
            
            # Measurement: expectation values of Z on qubits 0 and 1
            return [qml.expval(qml.PauliZ(0)), qml.expval(qml.PauliZ(1))]
        
        return circuit


class Sky130FeatureEncoder(nn.Module):
    """Extract and normalize Sky130-specific cell features."""
    
    # Sky130 unithd site dimensions (in DBU)
    SITE_WIDTH_DBU = 460  # 0.46 µm
    SITE_HEIGHT_DBU = 2720  # 2.72 µm
    
    def __init__(self, die_area: Tuple[float, float, float, float]):
        """
        Args:
            die_area: (x0, y0, x1, y1) in DBU
        """
        super().__init__()
        self.die_area = die_area
        self.die_width = die_area[2] - die_area[0]
        self.die_height = die_area[3] - die_area[1]
    
    def forward(self, cell_data: dict) -> np.ndarray:
        """
        Extract 8 Sky130-tuned features per cell.
        
        Features: [norm_width, norm_height, pin_count, fanout, fanin,
                   norm_x_init, norm_y_init, connectivity_score]
        
        Returns:
            Features array [N_cells, 8] normalized to [0, 1]
        """
        cells = cell_data.get('cells', [])
        n_cells = len(cells)
        
        if n_cells == 0:
            return np.zeros((0, 8))
        
        features = np.zeros((n_cells, 8))
        
        for i, cell in enumerate(cells):
            # Feature 0: Normalized cell width (relative to site width)
            width = cell.get('width', 0)
            features[i, 0] = min(1.0, width / (self.SITE_WIDTH_DBU * 10))
            
            # Feature 1: Normalized cell height (relative to row height)
            height = cell.get('height', 0)
            features[i, 1] = min(1.0, height / self.SITE_HEIGHT_DBU)
            
            # Feature 2: Pin count normalized [0, 1]
            pin_count = cell.get('pins', 0)
            features[i, 2] = min(1.0, pin_count / 20.0)
            
            # Feature 3: Fanout normalized [0, 1]
            fanout = cell.get('fanout', 0)
            features[i, 3] = min(1.0, fanout / 50.0)
            
            # Feature 4: Fanin normalized [0, 1]
            fanin = cell.get('fanin', 0)
            features[i, 4] = min(1.0, fanin / 50.0)
            
            # Feature 5: Normalized X position
            x = cell.get('x', 0)
            features[i, 5] = (x - self.die_area[0]) / self.die_width
            
            # Feature 6: Normalized Y position
            y = cell.get('y', 0)
            features[i, 6] = (y - self.die_area[1]) / self.die_height
            
            # Feature 7: Connectivity score (betweenness-like metric)
            conn_score = (pin_count + fanout + fanin) / 100.0
            features[i, 7] = min(1.0, conn_score)
        
        # Clamp all features to [0, 1]
        features = np.clip(features, 0.0, 1.0)
        
        return features


class QMLPlacementModel(nn.Module):
    """Complete QML placement model: encoder → VQC → decoder."""
    
    def __init__(self, n_qubits: int = 8, n_layers: int = 4,
                 die_area: Optional[Tuple[float, float, float, float]] = None):
        """
        Args:
            n_qubits: VQC qubits
            n_layers: VQC layers
            die_area: (x0, y0, x1, y1) in DBU for feature normalization
        """
        super().__init__()
        self.n_qubits = n_qubits
        self.n_layers = n_layers
        
        # Set default die area if not provided (Sky130 CA234 default)
        if die_area is None:
            die_area = (0, 0, 1000000, 1000000)  # 1000×1000 µm default
        
        self.die_area = die_area
        
        # Feature encoder (Sky130-specific)
        self.feature_encoder = Sky130FeatureEncoder(die_area)
        
        # Classical pre-encoder: project 8 features to qubit count
        self.pre_encoder = nn.Sequential(
            nn.Linear(8, 64),
            nn.LayerNorm(64),
            nn.GELU(),
            nn.Linear(64, n_qubits),
            nn.Tanh()  # Output in [-1, 1]
        )
        
        # Quantum circuit
        self.vqc = QuantumPlacementCircuit(n_qubits, n_layers)
        
        # Classical decoder
        self.decoder = nn.Sequential(
            nn.Linear(n_qubits, 64),
            nn.GELU(),
            nn.Linear(64, 64),
            nn.GELU(),
            nn.Linear(64, 2),
            nn.Sigmoid()  # Output [0, 1] for coordinates
        )
    
    def forward(self, cell_data: dict) -> np.ndarray:
        """
        Run complete placement model.
        
        Args:
            cell_data: Dictionary with 'cells', 'nets', 'die', 'rows', 'units' keys
            
        Returns:
            Placement coordinates [N_cells, 2] in DBU
        """
        # Extract features
        raw_features = self.feature_encoder(cell_data)
        
        if raw_features.shape[0] == 0:
            return np.zeros((0, 2))
        
        features_tensor = torch.FloatTensor(raw_features)
        
        # Pre-encode
        encoded = self.pre_encoder(features_tensor)
        
        # VQC
        quantum_output = self.vqc(encoded)
        
        # Decode to coordinates [0, 1]
        normalized_coords = self.decoder(quantum_output).detach().numpy()
        
        # Scale to die area (DBU)
        die_width = self.die_area[2] - self.die_area[0]
        die_height = self.die_area[3] - self.die_area[1]
        
        placements = np.zeros_like(normalized_coords)
        placements[:, 0] = self.die_area[0] + normalized_coords[:, 0] * die_width
        placements[:, 1] = self.die_area[1] + normalized_coords[:, 1] * die_height
        
        return placements
    
    def load_checkpoint(self, checkpoint_path: str):
        """Load pre-trained weights."""
        state_dict = torch.load(checkpoint_path, map_location='cpu')
        self.load_state_dict(state_dict)
        print(f"[QML] Loaded checkpoint: {checkpoint_path}")
    
    def save_checkpoint(self, checkpoint_path: str):
        """Save model weights."""
        torch.save(self.state_dict(), checkpoint_path)
        print(f"[QML] Saved checkpoint: {checkpoint_path}")
