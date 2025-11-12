from django.db import models

class KanoodleBoard(models.Model):
    name = models.CharField(max_length=100)
    width = models.IntegerField(default=5)
    height = models.IntegerField(default=11)

    def __str__(self):
        return str(self.name)

class Piece(models.Model):
    name = models.CharField(max_length=100, unique=True)
    shapeData = models.JSONField()
    color = models.CharField(max_length=7, default='#999999')

    def __str__(self):
        return str(self.name)

class partialSolution(models.Model):
    board = models.ForeignKey(KanoodleBoard, on_delete=models.CASCADE)
    state_data = models.JSONField(default=dict)
    def __str__(self):
        return f"Solution for {self.board.name} ({self.pk})"

